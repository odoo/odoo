# -*- coding: utf-8 -*-

from openerp.tests import common

class TestCrmLeadCopy(common.TransactionCase):

    def test_crm_lead_copy(self):
        """ Tests for Crm Lead Copy """

        # I make duplicate the Lead.
        self.env.ref("crm.crm_case_4").copy()
