# -*- coding: utf-8 -*-

from openerp.addons.crm.tests.test_crm_access_group_users import TestCrmAccessGroupUsers

class TestPhonecalls(TestCrmAccessGroupUsers):

    def test_phonecalls(self):
        """ Tests for Test Phonecalls """
        CrmPhonecall2phonecall = self.env['crm.phonecall2phonecall']

        # Salesman check the phone calls data so test with the access rights of salesman.

        # I schedule a phone call with a customer.
        context = {'active_model': 'crm.phonecall', 'active_ids': [self.env.ref("crm.crm_phonecall_6").id], 'active_id': self.env.ref("crm.crm_phonecall_6").id}
        calls = CrmPhonecall2phonecall.sudo(self.crm_res_users_salesman.id).with_context(context).create(
            dict(
                name='Proposition de réduction',
            ))
        calls.with_context(context).action_schedule()

        # I schedule a meeting based on this phone call.
        self.env.ref('crm.crm_phonecall_6').action_make_meeting()
