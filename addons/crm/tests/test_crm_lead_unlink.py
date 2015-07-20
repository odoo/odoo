# -*- coding: utf-8 -*-

from openerp.addons.crm.tests.test_crm_access_group_users import TestCrmAccessGroupUsers

class TestCrmLeadUnlink(TestCrmAccessGroupUsers):

    def test_crm_lead_unlink(self):
        """ Tests for Test Crm Lead unlink """

        # Only Sales manager Unlink the Lead so test with Manager's access rights'.
        self.env.ref('crm.crm_case_4').sudo(self.crm_res_users_salesmanager.id).unlink()
