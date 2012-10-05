#!/usr/bin/env python

'''
@brief Test to check CTD
@author Michael Meisinger
'''



from pyon.ion.stream import  StandaloneStreamPublisher
from pyon.public import log
from pyon.util.containers import DotDict
from pyon.util.file_sys import FileSystem
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import IonUnitTestCase
from pyon.util.containers import get_safe
from pyon.ion.stream import StandaloneStreamSubscriber
from nose.plugins.attrib import attr

from mock import Mock, sentinel, patch, mocksignature
from collections import defaultdict
from interface.objects import ProcessDefinition
from interface.services.dm.ipubsub_management_service import PubsubManagementServiceClient
from interface.objects import StreamRoute, Granule
from ion.processes.data.ctd_stream_publisher import SimpleCtdPublisher
from ion.processes.data.transforms.ctd.ctd_L0_all import ctd_L0_all
from ion.processes.data.transforms.ctd.ctd_L1_conductivity import CTDL1ConductivityTransform
from ion.processes.data.transforms.ctd.ctd_L1_pressure import CTDL1PressureTransform
from ion.processes.data.transforms.ctd.ctd_L1_temperature import CTDL1TemperatureTransform
from ion.processes.data.transforms.ctd.ctd_L2_salinity import SalinityTransform
from ion.processes.data.transforms.ctd.ctd_L2_density import DensityTransform
from interface.services.cei.iprocess_dispatcher_service import ProcessDispatcherServiceClient
from ion.services.dm.utility.granule.record_dictionary import RecordDictionaryTool
from ion.util.parameter_yaml_IO import get_param_dict
import unittest, os, gevent
from seawater.gibbs import SP_from_cndr, rho, SA_from_SP
from seawater.gibbs import cte

@attr('UNIT', group='ctd')
@unittest.skip('Not working')
class TestCtdTransforms(IonUnitTestCase):

    def setUp(self):
        # This test does not start a container so we have to hack creating a FileSystem singleton instance
#        FileSystem(DotDict())

        self.px_ctd = SimpleCtdPublisher()
        self.px_ctd.last_time = 0

        self.tx_L0 = ctd_L0_all()
        self.tx_L0.streams = defaultdict(Mock)
        self.tx_L0.cond_publisher = Mock()
        self.tx_L0.temp_publisher = Mock()
        self.tx_L0.pres_publisher = Mock()

        self.tx_L1_C = CTDL1ConductivityTransform()
        self.tx_L1_C.streams = defaultdict(Mock)

        self.tx_L1_T = CTDL1TemperatureTransform()
        self.tx_L1_T.streams = defaultdict(Mock)

        self.tx_L1_P = CTDL1PressureTransform()
        self.tx_L1_P.streams = defaultdict(Mock)

        self.tx_L2_S = SalinityTransform()
        self.tx_L2_S.streams = defaultdict(Mock)

        self.tx_L2_D = DensityTransform()
        self.tx_L2_D.streams = defaultdict(Mock)

    def test_transforms(self):

        length = 1

        packet = self.px_ctd._get_new_ctd_packet("STR_ID", length)

        log.debug("Packet: %s" % packet)

        self.tx_L0.process(packet)

        self.tx_L0.cond_publisher.publish = mocksignature(self.tx_L0.cond_publisher.publish)
        self.tx_L0.cond_publisher.publish.return_value = ''

        self.tx_L0.temp_publisher.publish = mocksignature(self.tx_L0.cond_publisher.publish)
        self.tx_L0.temp_publisher.publish.return_value = ''

        self.tx_L0.pres_publisher.publish = mocksignature(self.tx_L0.cond_publisher.publish)
        self.tx_L0.pres_publisher.publish.return_value = ''

        L0_cond = self.tx_L0.cond_publisher.publish.call_args[0][0]
        L0_temp = self.tx_L0.temp_publisher.publish.call_args[0][0]
        L0_pres = self.tx_L0.pres_publisher.publish.call_args[0][0]

        log.debug("L0 cond: %s" % L0_cond)
        log.debug("L0 temp: %s" % L0_temp)
        log.debug("L0 pres: %s" % L0_pres)

        L1_cond = self.tx_L1_C.execute(L0_cond)
        log.debug("L1 cond: %s" % L1_cond)

        L1_temp = self.tx_L1_T.execute(L0_temp)
        log.debug("L1 temp: %s" % L1_temp)

        L1_pres = self.tx_L1_P.execute(L0_pres)
        log.debug("L1 pres: %s" % L1_pres)

        L2_sal = self.tx_L2_S.execute(packet)
        log.debug("L2 sal: %s" % L2_sal)

        L2_dens = self.tx_L2_D.execute(packet)
        log.debug("L2 dens: %s" % L2_dens)

@attr('INT', group='dm')
class CtdTransformsIntTest(IonIntegrationTestCase):
    def setUp(self):
        super(CtdTransformsIntTest, self).setUp()

        self._start_container()
        self.container.start_rel_from_url('res/deploy/r2deploy.yml')

        self.queue_cleanup = []
        self.exchange_cleanup = []


        self.pubsub = PubsubManagementServiceClient()
        self.process_dispatcher = ProcessDispatcherServiceClient()

        self.exchange_name = 'ctd_L0_all_queue'
        self.exchange_point = 'test_exchange'

    def tearDown(self):
        for queue in self.queue_cleanup:
            xn = self.container.ex_manager.create_xn_queue(queue)
            xn.delete()
        for exchange in self.exchange_cleanup:
            xp = self.container.ex_manager.create_xp(exchange)
            xp.delete()


    @attr('LOCOINT')
    @unittest.skipIf(os.getenv('CEI_LAUNCH_TEST', False), 'Skip test while in CEI LAUNCH mode')
    def test_ctd_L0_all(self):
        '''
        Test that packets are processed by the ctd_L0_all transform
        '''

        #---------------------------------------------------------------------------------------------
        # Launch a ctd transform
        #---------------------------------------------------------------------------------------------
        # Create the process definition
        process_definition = ProcessDefinition(
            name='ctd_L0_all',
            description='For testing ctd_L0_all')
        process_definition.executable['module']= 'ion.processes.data.transforms.ctd.ctd_L0_all'
        process_definition.executable['class'] = 'ctd_L0_all'
        ctd_transform_proc_def_id = self.process_dispatcher.create_process_definition(process_definition=process_definition)

        # Build the config
        config = DotDict()
        config.process.queue_name = self.exchange_name
        config.process.exchange_point = self.exchange_point

        config.process.interval = 1.0

        cond_stream_id, _ = self.pubsub.create_stream('test_conductivity', exchange_point='science_data')
        config.process.publish_streams.conductivity = cond_stream_id

        temp_stream_id, _ = self.pubsub.create_stream('test_temperature', exchange_point='science_data')
        config.process.publish_streams.temperature = temp_stream_id

        pres_stream_id, _ = self.pubsub.create_stream('test_pressure',  exchange_point='science_data')
        config.process.publish_streams.pressure = pres_stream_id

        log.debug("config:: %s" % config)

        # Schedule the process
        pid = self.process_dispatcher.schedule_process(process_definition_id=ctd_transform_proc_def_id, configuration=config)

        #---------------------------------------------------------------------------------------------
        # Create subscribers that will receive the conductivity, temperature and pressure granules from
        # the ctd transform
        #---------------------------------------------------------------------------------------------
        ar_cond = gevent.event.AsyncResult()
        def subscriber1(m, r, s):
            ar_cond.set(m)
        sub_cond = StandaloneStreamSubscriber('sub_cond', subscriber1)
        self.addCleanup(sub_cond.stop)

        ar_temp = gevent.event.AsyncResult()
        def subscriber2(m,r,s):
            ar_temp.set(m)
        sub_temp = StandaloneStreamSubscriber('sub_temp', subscriber2)
        self.addCleanup(sub_temp.stop)

        ar_pres = gevent.event.AsyncResult()
        def subscriber3(m,r,s):
            ar_pres.set(m)
        sub_pres = StandaloneStreamSubscriber('sub_pres', subscriber3)
        self.addCleanup(sub_pres.stop)

        sub_cond_id = self.pubsub.create_subscription('subscription_cond',
                                                                            stream_ids=[cond_stream_id],
                                                                            exchange_name='sub_cond')

        sub_temp_id = self.pubsub.create_subscription('subscription_temp',
            stream_ids=[temp_stream_id],
            exchange_name='sub_temp')

        sub_pres_id = self.pubsub.create_subscription('subscription_pres',
            stream_ids=[pres_stream_id],
            exchange_name='sub_pres')

        self.pubsub.activate_subscription(sub_cond_id)
        self.pubsub.activate_subscription(sub_temp_id)
        self.pubsub.activate_subscription(sub_pres_id)

        self.queue_cleanup.append(sub_cond.xn.queue)
        self.queue_cleanup.append(sub_temp.xn.queue)
        self.queue_cleanup.append(sub_pres.xn.queue)

        sub_cond.start()
        sub_temp.start()
        sub_pres.start()

        #------------------------------------------------------------------------------------------------------
        # Use a StandaloneStreamPublisher to publish a packet that can be then picked up by a ctd transform
        #------------------------------------------------------------------------------------------------------

        # Do all the routing stuff for the publishing
        routing_key = 'stream_id.stream'
        stream_route = StreamRoute(self.exchange_point, routing_key)

        xn = self.container.ex_manager.create_xn_queue(self.exchange_name)
        xp = self.container.ex_manager.create_xp(self.exchange_point)
        xn.bind('stream_id.stream', xp)

        pub = StandaloneStreamPublisher('stream_id', stream_route)

        # Build a packet that can be published
        self.px_ctd = SimpleCtdPublisher()
        self.px_ctd.last_time = 0
        publish_granule = self.px_ctd._get_new_ctd_packet(length = 5)

        # Publish the packet
        pub.publish(publish_granule)

        #------------------------------------------------------------------------------------------------------
        # Make assertions about whether the ctd transform executed its algorithm and published the correct
        # granules
        #------------------------------------------------------------------------------------------------------

        # Get the granule that is published by the ctd transform post processing
        result_cond = ar_cond.get(timeout=10)
        result_temp = ar_temp.get(timeout=10)
        result_pres = ar_pres.get(timeout=10)

        log.debug("result_cond: %s" % result_cond)
        log.debug("result_temp: %s" % result_temp)
        log.debug("result_pres: %s" % result_pres)

        # Check that the transform algorithm was successfully executed
        self.check_granule_splitting(publish_granule, [result_cond, result_temp, result_pres])

    @attr('LOCOINT')
    @unittest.skipIf(os.getenv('CEI_LAUNCH_TEST', False), 'Skip test while in CEI LAUNCH mode')
    def test_ctd_L1_conductivity(self):
        '''
        Test that packets are processed by the ctd_L1_conductivity transform
        '''

        #---------------------------------------------------------------------------------------------
        # Launch a ctd transform
        #---------------------------------------------------------------------------------------------
        # Create the process definition
        process_definition = ProcessDefinition(
            name='CTDL1ConductivityTransform',
            description='For testing CTDL1ConductivityTransform')
        process_definition.executable['module']= 'ion.processes.data.transforms.ctd.ctd_L1_conductivity'
        process_definition.executable['class'] = 'CTDL1ConductivityTransform'
        ctd_transform_proc_def_id = self.process_dispatcher.create_process_definition(process_definition=process_definition)

        # Build the config
        config = DotDict()
        config.process.queue_name = self.exchange_name
        config.process.exchange_point = self.exchange_point

        config.process.interval = 1.0

        pdict = get_param_dict('simple_data_particle_parsed_param_dict')

        log.debug("pdict: %s" % pdict)
        log.debug("type of pdict: %s" % type(pdict))

        stream_def_id =  self.pubsub.create_stream_definition('cond_stream_def', parameter_dictionary=pdict.dump())
        cond_stream_id, _ = self.pubsub.create_stream('test_conductivity',
                                                        exchange_point='science_data',
                                                        stream_definition_id=stream_def_id)

        config.process.publish_streams.conductivity = cond_stream_id

        # Schedule the process
        self.process_dispatcher.schedule_process(process_definition_id=ctd_transform_proc_def_id, configuration=config)

        #---------------------------------------------------------------------------------------------
        # Create subscribers that will receive the conductivity, temperature and pressure granules from
        # the ctd transform
        #---------------------------------------------------------------------------------------------
        ar_cond = gevent.event.AsyncResult()
        def subscriber1(m, r, s):
            ar_cond.set(m)
        sub_cond = StandaloneStreamSubscriber('sub_cond', subscriber1)
        self.addCleanup(sub_cond.stop)

        sub_cond_id = self.pubsub.create_subscription('subscription_cond',
            stream_ids=[cond_stream_id],
            exchange_name='sub_cond')

        self.pubsub.activate_subscription(sub_cond_id)

        self.queue_cleanup.append(sub_cond.xn.queue)

        sub_cond.start()

        #------------------------------------------------------------------------------------------------------
        # Use a StandaloneStreamPublisher to publish a packet that can be then picked up by a ctd transform
        #------------------------------------------------------------------------------------------------------

        # Do all the routing stuff for the publishing
        routing_key = 'stream_id.stream'
        stream_route = StreamRoute(self.exchange_point, routing_key)

        xn = self.container.ex_manager.create_xn_queue(self.exchange_name)
        xp = self.container.ex_manager.create_xp(self.exchange_point)
        xn.bind('stream_id.stream', xp)

        pub = StandaloneStreamPublisher('stream_id', stream_route)

        # Build a packet that can be published
        self.px_ctd = SimpleCtdPublisher()
        self.px_ctd.last_time = 0
        publish_granule = self.px_ctd._get_new_ctd_packet(length = 5)

        # Publish the packet
        pub.publish(publish_granule)

        #------------------------------------------------------------------------------------------------------
        # Make assertions about whether the ctd transform executed its algorithm and published the correct
        # granules
        #------------------------------------------------------------------------------------------------------

        # Get the granule that is published by the ctd transform post processing
        result_cond = ar_cond.get(timeout=10)
        log.debug("result_cond: %s" % result_cond)

        self.assertTrue(isinstance(result_cond, Granule))

        rdt = RecordDictionaryTool.load_from_granule(result_cond)
        self.assertTrue(rdt.__contains__('conductivity'))

        self.check_cond_algorithm_execution(publish_granule, result_cond)

    def check_cond_algorithm_execution(self, publish_granule, granule_from_transform):

        input_rdt_to_transform = RecordDictionaryTool.load_from_granule(publish_granule)
        output_rdt_transform = RecordDictionaryTool.load_from_granule(granule_from_transform)

        output_data = output_rdt_transform['conductivity']
        input_data = input_rdt_to_transform['conductivity']

        self.assertTrue(((input_data / 100000.0) - 0.5).all() == output_data.all())

    def check_pres_algorithm_execution(self, publish_granule, granule_from_transform):

        input_rdt_to_transform = RecordDictionaryTool.load_from_granule(publish_granule)
        output_rdt_transform = RecordDictionaryTool.load_from_granule(granule_from_transform)

        output_data = output_rdt_transform['pressure']
        input_data = input_rdt_to_transform['pressure']

        self.assertTrue(input_data.all() == output_data.all())

    def check_temp_algorithm_execution(self, publish_granule, granule_from_transform):

        input_rdt_to_transform = RecordDictionaryTool.load_from_granule(publish_granule)
        output_rdt_transform = RecordDictionaryTool.load_from_granule(granule_from_transform)

        output_data = output_rdt_transform['temp']
        input_data = input_rdt_to_transform['temp']

        self.assertTrue(((input_data / 100000.0) - 10).all() == output_data.all())

    def check_density_algorithm_execution(self, publish_granule, granule_from_transform):

        #------------------------------------------------------------------
        # Calculate the correct density from the input granule data
        #------------------------------------------------------------------
        input_rdt_to_transform = RecordDictionaryTool.load_from_granule(publish_granule)
        output_rdt_transform = RecordDictionaryTool.load_from_granule(granule_from_transform)

        conductivity = input_rdt_to_transform['conductivity']
        pressure = input_rdt_to_transform['pressure']
        temperature = input_rdt_to_transform['temp']

        longitude = input_rdt_to_transform['lon']
        latitude = input_rdt_to_transform['lat']

        sp = SP_from_cndr(r=conductivity/cte.C3515, t=temperature, p=pressure)
        sa = SA_from_SP(sp, pressure, longitude, latitude)
        dens_value = rho(sa, temperature, pressure)

        out_density = output_rdt_transform['density']

        #-----------------------------------------------------------------------------
        # Check that the output data from the transform has the correct density values
        #-----------------------------------------------------------------------------
        self.assertTrue(dens_value.all() == out_density.all())

    def check_salinity_algorithm_execution(self, publish_granule, granule_from_transform):

        #------------------------------------------------------------------
        # Calculate the correct density from the input granule data
        #------------------------------------------------------------------
        input_rdt_to_transform = RecordDictionaryTool.load_from_granule(publish_granule)
        output_rdt_transform = RecordDictionaryTool.load_from_granule(granule_from_transform)

        conductivity = input_rdt_to_transform['conductivity']
        pressure = input_rdt_to_transform['pressure']
        temperature = input_rdt_to_transform['temp']

        longitude = input_rdt_to_transform['lon']
        latitude = input_rdt_to_transform['lat']

        sal_value = SP_from_cndr(r=conductivity/cte.C3515, t=temperature, p=pressure)

        out_salinity = output_rdt_transform['salinity']

        #-----------------------------------------------------------------------------
        # Check that the output data from the transform has the correct density values
        #-----------------------------------------------------------------------------
        self.assertTrue(sal_value.all() == out_salinity.all())

    def check_granule_splitting(self, publish_granule, out_granules):
        '''
        This checks that the ctd_L0_all transform is able to split out one of the
        granules from the whole granule
        fed into the transform
        '''

        input_rdt_to_transform = RecordDictionaryTool.load_from_granule(publish_granule)

        in_cond = input_rdt_to_transform['conductivity']
        in_pressure = input_rdt_to_transform['pressure']
        in_temp = input_rdt_to_transform['temp']

        out_cond = None
        out_pressure = None
        out_temp = None

        for out_granule in out_granules:
            output_rdt_transform = RecordDictionaryTool.load_from_granule(out_granule)
            if output_rdt_transform.__contains__('conductivity'):
                out_cond = output_rdt_transform['conductivity']
            elif output_rdt_transform.__contains__('pressure'):
                out_pressure = output_rdt_transform['pressure']
            elif output_rdt_transform.__contains__('temp'):
                out_temp = output_rdt_transform['temp']

        self.assertTrue(in_cond.all() == out_cond.all())
        self.assertTrue(in_pressure.all() == out_pressure.all())
        self.assertTrue(in_temp.all() == out_temp.all())

    @attr('LOCOINT')
    @unittest.skipIf(os.getenv('CEI_LAUNCH_TEST', False), 'Skip test while in CEI LAUNCH mode')
    def test_ctd_L1_pressure(self):
        '''
        Test that packets are processed by the ctd_L1_pressure transform
        '''

        #---------------------------------------------------------------------------------------------
        # Launch a ctd transform
        #---------------------------------------------------------------------------------------------
        # Create the process definition
        process_definition = ProcessDefinition(
            name='CTDL1PressureTransform',
            description='For testing CTDL1PressureTransform')
        process_definition.executable['module']= 'ion.processes.data.transforms.ctd.ctd_L1_pressure'
        process_definition.executable['class'] = 'CTDL1PressureTransform'
        ctd_transform_proc_def_id = self.process_dispatcher.create_process_definition(process_definition=process_definition)

        # Build the config
        config = DotDict()
        config.process.queue_name = self.exchange_name
        config.process.exchange_point = self.exchange_point

        config.process.interval = 1.0
        pres_stream_id, _ = self.pubsub.create_stream('test_pressure',
            exchange_point='science_data')

        config.process.publish_streams.pressure = pres_stream_id

        # Schedule the process
        self.process_dispatcher.schedule_process(process_definition_id=ctd_transform_proc_def_id, configuration=config)

        #---------------------------------------------------------------------------------------------
        # Create subscribers that will receive the pressure granules from
        # the ctd transform
        #---------------------------------------------------------------------------------------------

        ar_pres = gevent.event.AsyncResult()
        def subscriber3(m,r,s):
            ar_pres.set(m)
        sub_pres = StandaloneStreamSubscriber('sub_pres', subscriber3)
        self.addCleanup(sub_pres.stop)

        sub_pres_id = self.pubsub.create_subscription('subscription_pres',
            stream_ids=[pres_stream_id],
            exchange_name='sub_pres')

        self.pubsub.activate_subscription(sub_pres_id)

        self.queue_cleanup.append(sub_pres.xn.queue)

        sub_pres.start()

        #------------------------------------------------------------------------------------------------------
        # Use a StandaloneStreamPublisher to publish a packet that can be then picked up by a ctd transform
        #------------------------------------------------------------------------------------------------------

        # Do all the routing stuff for the publishing
        routing_key = 'stream_id.stream'
        stream_route = StreamRoute(self.exchange_point, routing_key)

        xn = self.container.ex_manager.create_xn_queue(self.exchange_name)
        xp = self.container.ex_manager.create_xp(self.exchange_point)
        xn.bind('stream_id.stream', xp)

        pub = StandaloneStreamPublisher('stream_id', stream_route)

        # Build a packet that can be published
        self.px_ctd = SimpleCtdPublisher()
        self.px_ctd.last_time = 0
        publish_granule = self.px_ctd._get_new_ctd_packet(length = 5)

        # Publish the packet
        pub.publish(publish_granule)

        #------------------------------------------------------------------------------------------------------
        # Make assertions about whether the ctd transform executed its algorithm and published the correct
        # granules
        #------------------------------------------------------------------------------------------------------

        # Get the granule that is published by the ctd transform post processing
        result = ar_pres.get(timeout=10)
        self.assertTrue(isinstance(result, Granule))

        rdt = RecordDictionaryTool.load_from_granule(result)
        self.assertTrue(rdt.__contains__('pressure'))

        self.check_pres_algorithm_execution(publish_granule, result)

    @attr('LOCOINT')
    @unittest.skipIf(os.getenv('CEI_LAUNCH_TEST', False), 'Skip test while in CEI LAUNCH mode')
    def test_ctd_L1_temperature(self):
        '''
        Test that packets are processed by the ctd_L1_temperature transform
        '''

        #---------------------------------------------------------------------------------------------
        # Launch a ctd transform
        #---------------------------------------------------------------------------------------------
        # Create the process definition
        process_definition = ProcessDefinition(
            name='CTDL1TemperatureTransform',
            description='For testing CTDL1TemperatureTransform')
        process_definition.executable['module']= 'ion.processes.data.transforms.ctd.ctd_L1_temperature'
        process_definition.executable['class'] = 'CTDL1TemperatureTransform'
        ctd_transform_proc_def_id = self.process_dispatcher.create_process_definition(process_definition=process_definition)

        # Build the config
        config = DotDict()
        config.process.queue_name = self.exchange_name
        config.process.exchange_point = self.exchange_point

        config.process.interval = 1.0
        temp_stream_id, _ = self.pubsub.create_stream('test_temperature',
            exchange_point='science_data')

        config.process.publish_streams.temperature = temp_stream_id

        # Schedule the process
        self.process_dispatcher.schedule_process(process_definition_id=ctd_transform_proc_def_id, configuration=config)

        #---------------------------------------------------------------------------------------------
        # Create subscriber that will receive the temperature granule from
        # the ctd transform
        #---------------------------------------------------------------------------------------------

        ar_temp = gevent.event.AsyncResult()
        def subscriber2(m,r,s):
            ar_temp.set(m)
        sub_temp = StandaloneStreamSubscriber('sub_temp', subscriber2)
        self.addCleanup(sub_temp.stop)

        sub_temp_id = self.pubsub.create_subscription('subscription_temp',
            stream_ids=[temp_stream_id],
            exchange_name='sub_temp')

        self.pubsub.activate_subscription(sub_temp_id)

        self.queue_cleanup.append(sub_temp.xn.queue)

        sub_temp.start()

        #------------------------------------------------------------------------------------------------------
        # Use a StandaloneStreamPublisher to publish a packet that can be then picked up by a ctd transform
        #------------------------------------------------------------------------------------------------------

        # Do all the routing stuff for the publishing
        routing_key = 'stream_id.stream'
        stream_route = StreamRoute(self.exchange_point, routing_key)

        xn = self.container.ex_manager.create_xn_queue(self.exchange_name)
        xp = self.container.ex_manager.create_xp(self.exchange_point)
        xn.bind('stream_id.stream', xp)

        pub = StandaloneStreamPublisher('stream_id', stream_route)

        # Build a packet that can be published
        self.px_ctd = SimpleCtdPublisher()
        self.px_ctd.last_time = 0
        publish_granule = self.px_ctd._get_new_ctd_packet(length = 5)

        # Publish the packet
        pub.publish(publish_granule)

        #------------------------------------------------------------------------------------------------------
        # Make assertions about whether the ctd transform executed its algorithm and published the correct
        # granules
        #------------------------------------------------------------------------------------------------------

        # Get the granule that is published by the ctd transform post processing
        result = ar_temp.get(timeout=10)
        self.assertTrue(isinstance(result, Granule))

        rdt = RecordDictionaryTool.load_from_granule(result)
        self.assertTrue(rdt.__contains__('temp'))

        self.check_temp_algorithm_execution(publish_granule, result)

    @attr('LOCOINT')
    @unittest.skipIf(os.getenv('CEI_LAUNCH_TEST', False), 'Skip test while in CEI LAUNCH mode')
    def test_ctd_L2_density(self):
        '''
        Test that packets are processed by the ctd_L1_density transform
        '''

        #---------------------------------------------------------------------------------------------
        # Launch a ctd transform
        #---------------------------------------------------------------------------------------------
        # Create the process definition
        process_definition = ProcessDefinition(
            name='DensityTransform',
            description='For testing DensityTransform')
        process_definition.executable['module']= 'ion.processes.data.transforms.ctd.ctd_L2_density'
        process_definition.executable['class'] = 'DensityTransform'
        ctd_transform_proc_def_id = self.process_dispatcher.create_process_definition(process_definition=process_definition)

        # Build the config
        config = DotDict()
        config.process.queue_name = self.exchange_name
        config.process.exchange_point = self.exchange_point

        config.process.interval = 1.0

        dens_stream_id, _ = self.pubsub.create_stream('test_density',
            exchange_point='science_data')
        config.process.publish_streams.density = dens_stream_id

        # Schedule the process
        self.process_dispatcher.schedule_process(process_definition_id=ctd_transform_proc_def_id, configuration=config)

        #---------------------------------------------------------------------------------------------
        # Create a subscriber that will receive the density granule from the ctd transform
        #---------------------------------------------------------------------------------------------

        ar_dens = gevent.event.AsyncResult()
        def subscriber3(m,r,s):
            ar_dens.set(m)
        sub_dens = StandaloneStreamSubscriber('sub_dens', subscriber3)
        self.addCleanup(sub_dens.stop)

        sub_dens_id = self.pubsub.create_subscription('subscription_dens',
            stream_ids=[dens_stream_id],
            exchange_name='sub_dens')

        self.pubsub.activate_subscription(sub_dens_id)

        self.queue_cleanup.append(sub_dens.xn.queue)

        sub_dens.start()

        #------------------------------------------------------------------------------------------------------
        # Use a StandaloneStreamPublisher to publish a packet that can be then picked up by a ctd transform
        #------------------------------------------------------------------------------------------------------

        # Do all the routing stuff for the publishing
        routing_key = 'stream_id.stream'
        stream_route = StreamRoute(self.exchange_point, routing_key)

        xn = self.container.ex_manager.create_xn_queue(self.exchange_name)
        xp = self.container.ex_manager.create_xp(self.exchange_point)
        xn.bind('stream_id.stream', xp)

        pub = StandaloneStreamPublisher('stream_id', stream_route)

        # Build a packet that can be published
        self.px_ctd = SimpleCtdPublisher()
        self.px_ctd.last_time = 0
        publish_granule = self.px_ctd._get_new_ctd_packet(length = 5)

        # Publish the packet
        pub.publish(publish_granule)

        #------------------------------------------------------------------------------------------------------
        # Make assertions about whether the ctd transform executed its algorithm and published the correct
        # granules
        #------------------------------------------------------------------------------------------------------

        # Get the granule that is published by the ctd transform post processing
        result = ar_dens.get(timeout=10)
        self.assertTrue(isinstance(result, Granule))

        rdt = RecordDictionaryTool.load_from_granule(result)
        self.assertTrue(rdt.__contains__('density'))

        self.check_density_algorithm_execution(publish_granule, result)

    @attr('LOCOINT')
    @unittest.skipIf(os.getenv('CEI_LAUNCH_TEST', False), 'Skip test while in CEI LAUNCH mode')
    def test_ctd_L2_salinity(self):
        '''
        Test that packets are processed by the ctd_L1_salinity transform
        '''

        #---------------------------------------------------------------------------------------------
        # Launch a ctd transform
        #---------------------------------------------------------------------------------------------
        # Create the process definition
        process_definition = ProcessDefinition(
            name='SalinityTransform',
            description='For testing SalinityTransform')
        process_definition.executable['module']= 'ion.processes.data.transforms.ctd.ctd_L2_salinity'
        process_definition.executable['class'] = 'SalinityTransform'
        ctd_transform_proc_def_id = self.process_dispatcher.create_process_definition(process_definition=process_definition)

        # Build the config
        config = DotDict()
        config.process.queue_name = self.exchange_name
        config.process.exchange_point = self.exchange_point

        config.process.interval = 1.0

        sal_stream_id, _ = self.pubsub.create_stream('test_salinity',
            exchange_point='science_data')

        config.process.publish_streams.salinity = sal_stream_id

        # Schedule the process
        self.process_dispatcher.schedule_process(process_definition_id=ctd_transform_proc_def_id, configuration=config)

        #---------------------------------------------------------------------------------------------
        # Create a subscriber that will receive the salinity granule from the ctd transform
        #---------------------------------------------------------------------------------------------

        ar_sal = gevent.event.AsyncResult()
        def subscriber3(m,r,s):
            ar_sal.set(m)
        sub_sal = StandaloneStreamSubscriber('sub_sal', subscriber3)
        self.addCleanup(sub_sal.stop)

        sub_sal_id = self.pubsub.create_subscription('subscription_sal',
            stream_ids=[sal_stream_id],
            exchange_name='sub_sal')

        self.pubsub.activate_subscription(sub_sal_id)

        self.queue_cleanup.append(sub_sal.xn.queue)

        sub_sal.start()

        #------------------------------------------------------------------------------------------------------
        # Use a StandaloneStreamPublisher to publish a packet that can be then picked up by a ctd transform
        #------------------------------------------------------------------------------------------------------

        # Do all the routing stuff for the publishing
        routing_key = 'stream_id.stream'
        stream_route = StreamRoute(self.exchange_point, routing_key)

        xn = self.container.ex_manager.create_xn_queue(self.exchange_name)
        xp = self.container.ex_manager.create_xp(self.exchange_point)
        xn.bind('stream_id.stream', xp)

        pub = StandaloneStreamPublisher('stream_id', stream_route)

        # Build a packet that can be published
        self.px_ctd = SimpleCtdPublisher()
        self.px_ctd.last_time = 0
        publish_granule = self.px_ctd._get_new_ctd_packet(length = 5)

        # Publish the packet
        pub.publish(publish_granule)

        #------------------------------------------------------------------------------------------------------
        # Make assertions about whether the ctd transform executed its algorithm and published the correct
        # granules
        #------------------------------------------------------------------------------------------------------

        # Get the granule that is published by the ctd transform post processing
        result = ar_sal.get(timeout=10)
        self.assertTrue(isinstance(result, Granule))

        rdt = RecordDictionaryTool.load_from_granule(result)
        self.assertTrue(rdt.__contains__('salinity'))

        self.check_salinity_algorithm_execution(publish_granule, result)
