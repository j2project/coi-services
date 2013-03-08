#!/usr/bin/env python

"""
@package ion.core.includes.mi_exceptions Exception classes for MI work
@file ion/services/mi/exceptions.py
@author Edward Hunter
@brief Common exceptions used in the MI work. Specific ones can be subclassed
in the driver code.
"""

#####
##  For goodish reasons this file is maintained in both the marine-integration
##  repository AND coi-services (HERE).  It is required to keep these files
##  synced.
##
##  To maintain backwards capability exceptions in this file should not be
##  changed or remove.  We should only add.
#####

__author__ = 'Edward Hunter'
__license__ = 'Apache 2.0'

from ion.agents.instrument.common import BaseEnum
import traceback

class InstErrorCode(BaseEnum):
    """Error codes generated by instrument drivers and agents"""
   
    TIMEOUT = ['ERROR_TIMEOUT','The message or operation timed out.']
    REQUIRED_PARAMETER = ['ERROR_REQUIRED_PARAMETER','A required parameter was not specified.']

class InstrumentException(Exception):
    """Base class for an exception related to physical instruments or their
    representation in ION.
    """
    
    def __init__ (self, msg=None, error_code=None):
        self.args = (error_code, msg)
        self.error_code = error_code
        self.msg = msg
    
class InstrumentConnectionException(InstrumentException):
    """Exception related to connection with a physical instrument"""
    pass

class InstrumentProtocolException(InstrumentException):
    """Exception related to an instrument protocol problem
    
    These are generally related to parsing or scripting of what is supposed
    to happen when talking at the lowest layer protocol to a device.
    @todo Add partial result property?
    """
    pass

class InstrumentStateException(InstrumentException):
    """Exception related to an instrument state of any sort"""
    pass

class InstrumentTimeoutException(InstrumentException):
    """Exception related to a command, request, or communication timing out"""
    def __init__(self, error_code=InstErrorCode.TIMEOUT, msg=None):
        InstrumentException.__init__(self, msg=msg, error_code=error_code)
    
class InstrumentDataException(InstrumentException):
    """Exception related to the data returned by an instrument or developed
    along the path of handling that data"""
    pass

class TestModeException(InstrumentException):
    """Attempt to run a test command while not in test mode"""
    pass

class InstrumentCommandException(InstrumentException):
    """A problem with the command sent toward the instrument"""
    pass
    
class InstrumentParameterException(InstrumentException):
    """A required parameter is not supplied"""
    def __init__(self, msg=None, error_code=None):
        if error_code == None:
            error_code = InstErrorCode.REQUIRED_PARAMETER
        if msg == None:
            msg = ""
            
        InstrumentException.__init__(self, error_code, msg)

class NotImplementedException(InstrumentException):
    """
    A driver function is not implemented.
    """
    pass

class ReadOnlyException(InstrumentException):
    """
    A driver function is not implemented.
    """
    pass

class SampleException(InstrumentException):
    """
    An expected sample could not be extracted.
    """
    pass

class SchedulerException(InstrumentException):
    """
    An error occurred in the scheduler
    """
    pass