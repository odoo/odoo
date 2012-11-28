

import datetime
import time

import tools
from openerp.tests.common import TransactionCase

import pdb
import netsvc

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
                                                    'is_company': True,
                                                    'state': 'draft'}, 
                                                context=None)
        self.followup_id = self.registry("ir.model.data").get_object_reference(cr, uid, "account_followup", "demo_followup1")[1]
        self.account_id = self.registry("ir.model.data").get_object_reference(cr, uid, "account", "a_sale")[1]
        self.journal_id = self.registry("ir.model.data").get_object_reference(cr, uid, "account", "bank_journal")[1]
        self.first_followup_line_id = self.registry("ir.model.data").get_object_reference(cr, uid, "account_followup", "demo_followup_line1")[1]
        self.product_id = self.registry("ir.model.data").get_object_reference(cr, uid, "product", "product_product_6")[1]
        self.invoice_id = self.invoice.create(cr, uid, {'partner_id': self.partner_id, 
                                                        'account_id': self.account_id, 
                                                        'journal_id': self.journal_id, 
                                                        'invoice_line': [(0, 0, {
                                                                            'name': "LCD Screen", 
                                                                            'product_id': self.product_id, 
                                                                            'quantity': 5, 
                                                                            'price_unit':200
                                                                                 })]}, context=None)
        
        print self.invoice.browse(cr, uid, self.invoice_id).state
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'account.invoice', self.invoice_id, 'invoice_open' , cr)
        print self.invoice.browse(cr, uid, self.invoice_id).state
        print self.invoice.browse(cr, uid, self.invoice_id).move_lines
#        context = {}
#        self.invoice.action_date_assign(cr, uid, [self.invoice_id])
#        self.invoice.action_move_create(cr, uid, [self.invoice_id], context=context)
#        self.invoice.action_number(cr, uid, [self.invoice_id], context=context)
#        self.invoice.invoice_validate(cr, uid, [self.invoice_id], context=context)
        print self.invoice.browse(cr, uid, self.invoice_id, context=None).date_due
        
        
        
    def test_00_send_followup_after_3_days(self):
        cr, uid = self.cr, self.uid
        self.wizard_id = self.wizard.create(cr, uid, {
                                                      'date':datetime.datetime.now().strftime("%Y-%m-%d"), 
                                                      'followup_id': self.followup_id
                                                      }, context={"followup_id": self.followup_id})
        res = self.wizard.do_process(cr, uid, [self.wizard_id], context={"followup_id": self.followup_id})
        print res
        self.assertFalse(self.partner.browse(cr, uid, self.partner_id).latest_followup_level_id)
        
    def test_05_send_followup__later_for_upgrade(self):
        cr, uid = self.cr, self.uid
        
        current_date = datetime.datetime.now()
        delta = datetime.timedelta(days=40)
        result = current_date + delta
        print "Resulting date", result
        self.wizard_id = self.wizard.create(cr, uid, {
                                                      'date':result.strftime("%Y-%m-%d"), 
                                                      'followup_id': self.followup_id
                                                      }, context={"followup_id": self.followup_id})
        res = self.wizard.do_process(cr, uid, [self.wizard_id], context={"followup_id": self.followup_id})
        pdb.set_trace()
        print res
        print self.partner.browse(cr, uid, self.partner_id).name
        print self.partner.browse(cr, uid, self.partner_id).latest_followup_level_id
        print self.partner.browse(cr, uid, self.partner_id).latest_followup_date
        self.assertEqual(self.partner.browse(cr, uid, self.partner_id).latest_followup_level_id.id, self.first_followup_line_id, 
                                            "Not updated to the correct follow-up level")
        
        
    def test_10_check_manual_action_done(self):
        cr, uid = self.cr, self.uid
        
        current_date = datetime.datetime.now()
        delta = datetime.timedelta(days=40)
        result = current_date + delta
        print "Resulting date", result
        self.wizard_id = self.wizard.create(cr, uid, {
                                                      'date':result.strftime("%Y-%m-%d"), 
                                                      'followup_id': self.followup_id
                                                      }, context={"followup_id": self.followup_id})
        res = self.wizard.do_process(cr, uid, [self.wizard_id], context={"followup_id": self.followup_id})
        self.wizard_id = self.wizard.create(cr, uid, {
                                                      'date':result.strftime("%Y-%m-%d"), 
                                                      'followup_id': self.followup_id
                                                      }, context={"followup_id": self.followup_id})
        print res
        res = self.wizard.do_process(cr, uid, [self.wizard_id], context={"followup_id": self.followup_id})
        self.assertEqual(self.partner.browse(cr, uid, self.partner_id).payment_next_action, "Call the customer on the phone!", "Manual action not set")
        print res
        
        