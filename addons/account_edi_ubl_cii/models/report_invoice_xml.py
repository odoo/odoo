# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang


class ReportInvoiceXml(models.AbstractModel):
    _name = 'report.account_edi_ubl_cii.report_invoice_xml_readable'
    _description = 'Invoice rendered from its XML'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        data_by_move = {}
        for move in docs:
            invoice_data = move._get_xml_invoice_data()
            if not invoice_data:
                raise UserError(_(
                    "No electronic invoice (UBL, CII or Factur-X) is attached to %s.",
                    move.display_name,
                ))
            invoice_data['payment_means_label'] = self._payment_means_label(
                invoice_data.get('payment_means_code'), invoice_data.get('payment_means_name'),
            )
            for line in invoice_data.get('lines') or []:
                line['unit'] = self._unit_label(line.get('unit'))
            data_by_move[move.id] = invoice_data
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'xml_data': data_by_move,
            'format_amount': self._format_amount,
        }

    @api.model
    def _payment_means_label(self, code, name):
        if name:
            return name
        labels = {
            '10': _("Cash"),
            '20': _("Cheque"),
            '30': _("Credit transfer"),
            '31': _("Debit transfer"),
            '42': _("Payment to bank account"),
            '48': _("Bank card"),
            '49': _("Direct debit"),
            '57': _("Standing agreement"),
            '58': _("SEPA credit transfer"),
            '59': _("SEPA direct debit"),
            '97': _("Clearing between partners"),
        }
        return labels.get((code or '').strip(), code or '')

    @api.model
    def _unit_label(self, code):
        labels = {
            'C62': _("Unit"),
            'EA': _("Unit"),
            'HUR': _("Hour"),
            'DAY': _("Day"),
            'KGM': _("kg"),
            'LTR': _("L"),
            'MTR': _("m"),
        }
        code = (code or '').strip()
        return labels.get(code, code)

    @api.model
    def _format_amount(self, value, currency=''):
        if value in (None, ''):
            return ''
        try:
            formatted = formatLang(self.env, float(value), digits=2)
        except (TypeError, ValueError):
            return value
        return ('%s %s' % (formatted, currency)).strip()
