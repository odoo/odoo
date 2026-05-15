# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_sg_permit_number = fields.Char(string="Permit No.")

    l10n_sg_permit_number_date = fields.Date(string="Date of permit number")

    def _get_name_invoice_report(self):
        self.ensure_one()
        # In SG, GST-registered companies (i.e. with a `vat`) will issue a "tax invoice".
        if self.company_id.account_fiscal_country_id.code == 'SG' and self.company_id.vat:
            return 'l10n_sg.report_invoice_document'
        return super()._get_name_invoice_report()
