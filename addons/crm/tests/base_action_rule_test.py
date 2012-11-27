import tools
from openerp.tests import common

class base_action_rule_test(common.TransactionCase):

    def setUp(self):
        """*****setUp*****"""
        super(base_action_rule_test, self).setUp()
        cr, uid = self.cr, self.uid

        """*****TeamCreation******"""
        self.team_pool = self.registry('crm.case.section')
        self.team_1_id = self.team_pool.create(cr, uid, {
            'name' : "Team 1",
            'active' : 1,
            'user_id' : uid,
            'complete_name' : "Test / Team 1",
            }, context=None)
        self.team_2_id = self.team_pool.create(cr, uid, {
            'name' : "Team 2",
            'active' : 1,
            'user_id' : uid,
            'complete_name' : "Test / Team 2",
            }, context=None)        

    def create_rule_1(self, cr, uid, context=None):
        """
            The "Rule 1" says that when a lead goes to the 'open' state, the team responsible for that lead changes to "Team 1"
        """
        self.action_pool = self.registry('base.action.rule')
        self.rule_1_id = self.action_pool.create(cr,uid,{
            'name' : "Rule 1",
            'model_id' : self.registry('ir.model').search(cr, uid, [('model','=','crm.lead')], context=context)[0],
            'active' : 1,
            'trg_state_to' : 'open',
            'trg_date_type' : 'none',
            'act_section_id' : self.team_1_id,
            }, context=context)

    def create_rule_2(self, cr, uid, context=None):
        """
            The "Rule 2" says that when a lead goes from 'open' state to 'done' state, the team responsible for that lead changes to "Team 2" 
        """
        self.action_pool = self.registry('base.action.rule')
        self.rule_2_id = self.action_pool.create(cr,uid,{
            'name' : "Rule 2",
            'model_id' : self.registry('ir.model').search(cr, uid, [('model','=','crm.lead')], context=context)[0],
            'active' : 1,
            'trg_state_to' : 'done',
            'trg_state_from' : 'open',
            'trg_date_type' : 'none',
            'act_section_id' : self.team_2_id,
            }, context=context)

    def test_00_check_to_state_draft(self):
        """
            This test check that the team change when the state is open but doesn't change when the state is different
        """
        cr, uid = self.cr, self.uid
        context = {}
        #First we need to create the Rule 1
        self.create_rule_1(cr, uid, context)
        #Once it is done, we can create a new lead (with a state = 'draft')
            #first we get our team 1
        self.team_1 = self.team_pool.browse(cr,uid,self.team_1_id,context=context)
            #We get a lead
        self.lead_1 = self.registry('ir.model.data').get_object_reference(cr, uid, 'crm', 'crm_case_1')
            #We change the team of crm_case_1

