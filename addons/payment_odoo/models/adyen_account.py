# -*- coding: utf-8 -*-

from odoo import models

class AdyenAccount(models.Model):
    _inherit = 'adyen.account'

    def unlink(self):
        acquirer = self.env['payment.acquirer'].search([('provider', '=', 'odoo'), ('odoo_adyen_account_id', 'in', self.ids)])
        acquirer.state = 'disabled'
        return super().unlink()
