#!/usr/bin/env python

"""Process that loads the system policy"""
__author__ = 'Stephen P. Henrie'

"""
Process that loads the system policy
"""
from pyon.public import CFG, log, ImmediateProcess, iex, Container, IonObject, RT, OT
from interface.services.coi.iidentity_management_service import IdentityManagementServiceProcessClient
from interface.services.coi.iorg_management_service import OrgManagementServiceProcessClient
from interface.services.coi.ipolicy_management_service import PolicyManagementServiceProcessClient

from pyon.public import CFG, log, ImmediateProcess, iex, Container

class LoadSystemPolicy(ImmediateProcess):
    """
    bin/pycc -x ion.processes.bootstrap.load_system_policy.LoadSystemPolicy op=load
    """
    def on_init(self):
        pass

    def on_start(self):
        op = self.CFG.get("op", None)
        log.info("LoadSystemPolicy: {op=%s}" % op)
        if op:
            if op == "load":
                self.op_load_system_policies(self)
            else:
                raise iex.BadRequest("Operation unknown")
        else:
            raise iex.BadRequest("No operation specified")

    def on_quit(self):
        pass

    #
    # Create the initial set of policy rules for the ION system. To make the rules easier to write, start by
    # denying all anonymous access to Org services and then add rules which Permit access to specific operations
    # based on conditions.
    #
    @classmethod
    def op_load_system_policies(cls, calling_process):

        org_client = OrgManagementServiceProcessClient(node=Container.instance.node, process=calling_process)
        ion_org = org_client.find_org()

        id_client = IdentityManagementServiceProcessClient(node=Container.instance.node, process=calling_process )

        system_actor = Container.instance.governance_controller.get_system_actor()
        log.info('system actor:' + system_actor._id)

        sa_user_header = Container.instance.governance_controller.get_system_actor_header()

        policy_client = PolicyManagementServiceProcessClient(node=Container.instance.node, process=calling_process)


        timeout = 20


##############
        '''
        This rule must be loaded before the Deny_Everything rule
        '''

        policy_client = PolicyManagementServiceProcessClient(node=Container.instance.node, process=calling_process)

        policy_text = '''
        <Rule RuleId="%s:" Effect="Permit">
            <Description>
                %s
            </Description>

            <Target>

                <Resources>
                    <Resource>
                        <ResourceMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-regexp-match">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">.</AttributeValue>
                            <ResourceAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:resource:resource-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ResourceMatch>
                    </Resource>
                </Resources>

            </Target>

            <Condition>
                    <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-at-least-one-member-of">
                        <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-bag">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">ION_MANAGER</AttributeValue>
                        </Apply>
                        <SubjectAttributeDesignator
                             AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-role-id"
                             DataType="http://www.w3.org/2001/XMLSchema#string"/>
                    </Apply>
            </Condition>

        </Rule>
        '''

        policy_id = policy_client.create_common_service_access_policy( 'Org_Manager_Permit_Everything',
            'A global Org policy rule that permits access to everything in the Org for a user with Org Manager or ION Manager role',
            policy_text, headers=sa_user_header)

##############


        '''
        This rule must be loaded before the Deny_Everything rule
        '''

        policy_text = '''
        <Rule RuleId="%s" Effect="Permit">
            <Description>
                %s
            </Description>

            <Target>

                <Subjects>
                    <Subject>
                        <SubjectMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">anonymous</AttributeValue>
                            <SubjectAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </SubjectMatch>
                    </Subject>
                </Subjects>


                <Actions>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-regexp-match">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">read</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-regexp-match">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">find</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-regexp-match">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">get</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">signon</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                </Actions>

            </Target>

            <Condition>
                <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:not">

                    <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-at-least-one-member-of">
                        <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-bag">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">find_requests</AttributeValue>
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">find_user_requests</AttributeValue>
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">find_enrolled_users</AttributeValue>
                        </Apply>
                        <ActionAttributeDesignator
                             AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id"
                             DataType="http://www.w3.org/2001/XMLSchema#string"/>
                    </Apply>
                </Apply>
            </Condition>

        </Rule>
        '''

        policy_id = policy_client.create_common_service_access_policy( 'Allowed_Anonymous_Service_Operations',
            'A global Org policy rule which specifies operations that are allowed with anonymous access',
            policy_text, headers=sa_user_header)



###############


        policy_text = '''
        <Rule RuleId="%s" Effect="Deny">
            <Description>
                %s
            </Description>

            <Target>

                <Subjects>
                    <Subject>
                        <SubjectMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">anonymous</AttributeValue>
                            <SubjectAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </SubjectMatch>
                    </Subject>
                </Subjects>
            </Target>


        </Rule>
        '''

        policy_id = policy_client.create_common_service_access_policy( 'Deny_Everything_For_Anonymous',
            'A global Org policy rule that denies everything as the base policy rule for anonymous users',
            policy_text, headers=sa_user_header)


###############

        policy_text = '''
           <Rule RuleId="%s" Effect="Permit">
            <Description>
                %s

            </Description>

            <Target>

                <Subjects>
                    <Subject>
                        <SubjectMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">anonymous</AttributeValue>
                            <SubjectAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </SubjectMatch>
                    </Subject>
                </Subjects>

                <Resources>
                    <Resource>
                        <ResourceMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">resource_registry</AttributeValue>
                            <ResourceAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:resource:resource-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ResourceMatch>
                    </Resource>
                </Resources>


                <Actions>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">create</AttributeValue>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">create_association</AttributeValue>
                        </ActionMatch>
                    </Action>
                </Actions>

            </Target>
            <Condition>

                <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                    <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-one-and-only">
                        <SubjectAttributeDesignator
                                AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-sender-id"
                                DataType="http://www.w3.org/2001/XMLSchema#string"/>
                    </Apply>
                    <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">identity_management</AttributeValue>
                    <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">policy_management</AttributeValue>
                </Apply>

            </Condition>

        </Rule>
        '''

        policy_id = policy_client.create_service_access_policy('resource_registry', 'RR_Anonymous_Bootstrap',
            'Permit anonymous access to these operations in the Resource Registry Service if called from the Identity Management Service',
            policy_text, headers=sa_user_header)



##############


        policy_text = '''
        <Rule RuleId="%s" Effect="Permit">
            <Description>
                %s

            </Description>

            <Target>

                <Subjects>
                    <Subject>
                        <SubjectMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">anonymous</AttributeValue>
                            <SubjectAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </SubjectMatch>
                    </Subject>
                </Subjects>

                <Resources>
                    <Resource>
                        <ResourceMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">identity_management</AttributeValue>
                            <ResourceAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:resource:resource-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ResourceMatch>
                    </Resource>
                </Resources>

                <Actions>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">create_actor_identity</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                </Actions>

            </Target>

            <Condition>

                <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                    <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-one-and-only">
                        <SubjectAttributeDesignator
                                AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-sender-id"
                                DataType="http://www.w3.org/2001/XMLSchema#string"/>
                    </Apply>
                    <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">bootstrap</AttributeValue>
                </Apply>

            </Condition>
        </Rule>
        '''

        policy_id = policy_client.create_service_access_policy('identity_management', 'IMS_Anonymous_Bootstrap',
            'Permit anonymous access to these operations in the Identity Management Service if called from the Bootstrap Service',
             policy_text, headers=sa_user_header)




##############


        policy_text = '''
            <Rule RuleId="%s" Effect="Deny">
            <Description>
                %s
            </Description>

            <Target>

                <Resources>
                    <Resource>
                        <ResourceMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">org_management</AttributeValue>
                            <ResourceAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:resource:resource-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ResourceMatch>
                    </Resource>
                </Resources>

                <Actions>

                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">find_requests</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">find_enrolled_users</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">approve_request</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">deny_request</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">enroll_member</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">cancel_member_enrollment</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">grant_role</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">revoke_role</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">add_user_role</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">remove_user_role</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">acquire_resource</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">release_resource</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                </Actions>

            </Target>

            <Condition>
                <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:not">
                    <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-at-least-one-member-of">
                        <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-bag">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">ORG_MANAGER</AttributeValue>
                        </Apply>
                        <SubjectAttributeDesignator
                             AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-role-id"
                             DataType="http://www.w3.org/2001/XMLSchema#string"/>
                    </Apply>
                </Apply>
            </Condition>

        </Rule> '''

        policy_id = policy_client.create_service_access_policy('org_management', 'OMS_Org_Manager_Role_Permitted',
            'Deny these operations in the Org Management Service if not the role of Org Manager',
             policy_text, headers=sa_user_header)

        ##############


        policy_text = '''
            <Rule RuleId="%s" Effect="Deny">
            <Description>
                %s
            </Description>

            <Target>

               <Resources>
                    <Resource>
                        <ResourceMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">instrument_management</AttributeValue>
                            <ResourceAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:resource:resource-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ResourceMatch>
                    </Resource>
                </Resources>

                <Actions>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-regexp-match">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">create</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-regexp-match">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">update</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-regexp-match">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">delete</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                </Actions>

            </Target>

            <Condition>
               <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:not">
                    <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-at-least-one-member-of">
                        <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-bag">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">INSTRUMENT_OPERATOR</AttributeValue>
                        </Apply>
                        <SubjectAttributeDesignator
                             AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-role-id"
                             DataType="http://www.w3.org/2001/XMLSchema#string"/>
                    </Apply>
                </Apply>
            </Condition>


        </Rule> '''

        policy_id = policy_client.create_service_access_policy('instrument_management', 'IMS_Instrument_Operator_Role_Permitted',
            'Deny these operations in the Instrument Management Service if not the role of Instrument Operator',
             policy_text, headers=sa_user_header)


        ##############


        policy_text = '''
            <Rule RuleId="%s" Effect="Deny">
            <Description>
                %s
            </Description>

            <Target>

               <Resources>
                    <Resource>
                        <ResourceMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">InstrumentDevice</AttributeValue>
                            <ResourceAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:resource:resource-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ResourceMatch>
                    </Resource>
                </Resources>

                <Actions>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-regexp-match">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">execute</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">set_param</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                    <Action>
                        <ActionMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">set_agent_param</AttributeValue>
                            <ActionAttributeDesignator AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </ActionMatch>
                    </Action>
                </Actions>

            </Target>

            <Condition>
                <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:not">
                    <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-at-least-one-member-of">
                        <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-bag">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">INSTRUMENT_OPERATOR</AttributeValue>
                        </Apply>
                        <SubjectAttributeDesignator
                             AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-role-id"
                             DataType="http://www.w3.org/2001/XMLSchema#string"/>
                    </Apply>
                </Apply>
            </Condition>


        </Rule> '''

        #All resource_agents are kind of handled the same - but the resource-id in the rule is set to the specific type
        policy_id = policy_client.create_service_access_policy('InstrumentDevice', 'RA_Instrument_Operator_Role_Permitted',
            'Deny these operations in an instrument agent if not the role of Instrument Operator',
            policy_text, headers=sa_user_header)

