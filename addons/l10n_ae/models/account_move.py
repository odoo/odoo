# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):

    _inherit = 'account.move'

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code == 'AE':
            return 'l10n_ae.report_invoice'
        return super()._get_name_invoice_report()
