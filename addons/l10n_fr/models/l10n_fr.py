# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    siret = fields.Char(string='SIRET', size=14)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_accounting_date(self, invoice_date, has_tax):
        if self.company_id._is_vat_french() and self.is_sale_document(include_receipts=True):
            # According to the french law invoice_date == date for customer invoice.
            return invoice_date
        return super()._get_accounting_date(invoice_date, has_tax)

    @api.constrains('move_type', 'date', 'invoice_date')
    def _check_french_date_invoice_date(self):
        moves = self.filtered(lambda move: move.company_id._is_vat_french() and move.date and move.invoice_date \
                              and move.is_sale_document(include_receipts=True) and move.date != move.invoice_date)
        if moves:
            raise ValidationError(_('According to the french law, date and invoice_date of customer invoice should be the same.\n'
                                    'Problematic numbers: %s\n', ', '.join(moves.mapped('name')))


class ChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        journals = super(ChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict)
        if company.country_id.code == "FR":
            #For France, sale/purchase journals must have a dedicated sequence for refunds
            for journal in journals:
                if journal['type'] in ['sale', 'purchase']:
                    journal['refund_sequence'] = True
        return journals
