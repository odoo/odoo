

from datetime import datetime

import tools
from openerp.tests.common import TransactionCase

class TestAccountFollowup(TransactionCase):
    def setUp(self):
        """ setUp ***"""
        super(TestAccountFollowup, self).setUp()
        cr, uid = self.cr, self.uid
        
        self.user = self.registry('res.users')
        self.user_id = self.user.browse(cr, uid, uid)
        self.partner = self.registry('res.partner')
        self.invoice = self.registry('account.invoice')
        self.invoice_line = self.registry('account.invoice.line')
        self.wizard = self.registry('account_followup.print')
        self.followup_id = self.registry('account_followup.followup')
        
        self.partner_id = self.partner.create(cr, uid, {'name':'Test Company', 
                                                    'email':'test@localhost',
                                                    'is_company': True,}, 
                                                context=None)
        self.followup_id = self.registry("ir.model.data").get_object_reference(cr, uid, "account_followup", "demo_followup1")[1]
        self.account_id = self.registry("ir.model.data").get_object_reference(cr, uid, "account", "a_sale")[1]
        self.invoice_id = self.invoice.create(cr, uid, {'partner_id': self.partner_id, 
                                                        'account_id': self.account_id, 
                                                        }, context=None)
        #self.invoice_line_id = self.invoice_line.create(cr, uid, {'name': 'Product A',
#                                                                  'quantity': 5,
#                                                                  'price':251.21, 
#                                                                  'invoice_id':self.invoice_id},
#                                                        context=None)
        #self.invoice.write(cr, uid, self.invoice_id, {'invoice_line': (4, self.invoice_line_id, {})})
#        self.invoice.action_date_assign(cr, uid, self.invoice_id)
#        self.invoice.action_move_create(cr, uid, self.invoice_id, context=None)
#        self.invoice.action_number(cr, uid, self.invoice_id, context=None)
#        self.invoice.invoice_validate(cr, uid, self.invoice_id, context=None)
        
        
        
    def test_00_send_followup_after_3_days(self):
        cr, uid = self.cr, self.uid
        self.wizard_id = self.wizard.create(cr, uid, {
                                                      'date':datetime.now().strftime("%Y-%m-%d"), 
                                                      'followup_id': self.followup_id
                                                      }, context={"followup_id": self.followup_id})
        self.wizard.do_process(cr, uid, [self.wizard_id], context={"followup_id": self.followup_id})
        self.assertFalse(self.partner.browse(cr, uid, self.partner_id).latest_followup_level_id)
        self.wizard_id = self.wizard.create(cr, uid, {
                                                      'date':(datetime.now() + datetime.timedelta(days=15)).strftime("%Y-%m-%d"), 
                                                      'followup_id': self.followup_id
                                                      }, context={"followup_id": self.followup_id})
        self.wizard.do_process(cr, uid, [self.wizard_id], context={"followup_id": self.followup_id})
        self.assertTrue(self.partner.browse(cr, uid, self.partner_id).latest_followup_level_id)
    
    
    
    
    