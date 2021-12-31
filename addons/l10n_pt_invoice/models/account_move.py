# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pt_qr_code_str = fields.Char(string='QR Code', compute='_compute_qr_code_str')

    @api.depends('amount_total', 'amount_untaxed', 'company_id', 'company_id.vat')
    def _compute_qr_code_str(self):
        """ Generate the qr code for Portugal invoicing.
        """
        def get_qr_encoding(tag, field):
            company_name_byte_array = field.encode('UTF-8')
            company_name_tag_encoding = tag.to_bytes(length=1, byteorder='big')
            company_name_length_encoding = len(company_name_byte_array).to_bytes(length=1, byteorder='big')
            return company_name_tag_encoding + company_name_length_encoding + company_name_byte_array

        for record in self:
            qr_code_str = ''
            if record.company_id.vat:
                # seller_name_enc = get_qr_encoding(1, record.company_id.display_name)
                # company_vat_enc = get_qr_encoding(2, record.company_id.vat)
                # invoice_total_enc = get_qr_encoding(4, str(record.amount_total))
                # total_vat_enc = get_qr_encoding(5, str(record.currency_id.round(record.amount_total - record.amount_untaxed)))

                qr_code_str = "RIIIIIIIIIIIIIIIIIIIICARDO"
            record.l10n_pt_qr_code_str = qr_code_str
