# -*- coding: utf-8 -*-

from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def setting_init_bank_account_action(self):
        """
        Override the "setting_init_bank_account_action" in accounting menu
        and change the flow for the "Add a bank account" menu item in dashboard.
        """
        return self.env['account.online.link'].action_new_synchronization()
