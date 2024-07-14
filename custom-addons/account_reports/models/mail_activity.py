# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountTaxReportActivity(models.Model):
    _inherit = "mail.activity"

    def action_open_tax_report(self):
        self.ensure_one()
        move = self.env['account.move'].browse(self.res_id)
        return move.action_open_tax_report()
