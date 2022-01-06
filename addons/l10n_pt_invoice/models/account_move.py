# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_date, float_repr
import re


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pt_qr_code_str = fields.Char(string='QR Code', compute='_compute_qr_code_str')

    def check_necessary_fields(self):
        # Check needed values are filled before creating the QR code
        for record in self:  # record is of type account.move
            if record.company_id.country_id.code != "PT":
                continue

            company_vat_not_ok = not self.company_id.vat or not re.match("([0-9]{9})+|([^^]+ [0-9/]+)", record.company_id.vat)
            partner_country_not_ok = not record.partner_id.country_id
            record_type_not_ok = record.type not in {'out_invoice', 'out_refund', 'out_receipt'}

            if company_vat_not_ok or partner_country_not_ok or record_type_not_ok:
                error_msg = "Some fields required for the generation of the document are missing or invalid. Please verify them:\n"
                error_msg += _('The `VAT` of your company should be defined and match the following format: 123456789\n') if company_vat_not_ok else ""
                error_msg += _('The `country of the customer should be defined.\n') if partner_country_not_ok else ""
                error_msg += _('The type of document should either be an invoice, a credit note, or a receipt\n') if record_type_not_ok else ""
                raise UserError(error_msg)

    def preview_invoice(self):
        self.check_necessary_fields()
        super().preview_invoice()

    def action_invoice_sent(self):
        self.check_necessary_fields()
        super().action_invoice_sent()

    @api.depends('partner_id', 'currency_id', 'date', 'type', 'display_name', 'amount_by_group', 'amount_total',
                 'amount_untaxed', 'company_id', 'company_id.vat', 'company_id.country_id', 'partner_id.country_id')
    def _compute_qr_code_str(self):
        """ Generate the informational QR code for Portugal invoicing.
        E.g.: A:509445535*B:123456823*C:BE*D:FT*E:N*F:20220103*G:FT 01P2022/1*H:0*I1:PT*I7:325.20*I8:74.80*N:74.80*O:400.00*P:0.00*Q:P0FE*R:2230
        """

        def get_base_and_vat(amount_by_group, vat_name, currency):
            vat_names = [line[0] for line in amount_by_group]
            vat_values = [line[1] for line in amount_by_group]
            vat_bases = [line[2] for line in amount_by_group]
            if vat_name not in vat_names:
                return False
            index = vat_names.index(vat_name)
            return {'base': float_repr(vat_bases[index], currency.decimal_places),
                    'vat': float_repr(vat_values[index], currency.decimal_places)}

        for record in self:  # record is of type account.move
            if record.company_id.country_id.code != "PT":
                continue

            qr_code_str = ""
            qr_code_str += f"A:{record.company_id.vat}*"
            qr_code_str += f"B:{record.partner_id.vat or '999999990'}*"
            qr_code_str += f"C:{record.partner_id.country_id.code}*"
            invoice_type_map = {
                "out_invoice": "FT",
                "out_refund": "NC",
                "out_receipt": "FR",
            }
            qr_code_str += f"D:{invoice_type_map[record.type]}*"
            qr_code_str += f"E:N*"
            qr_code_str += f"F:{format_date(self.env, record.date, date_format='yyyyMMdd')}*"
            qr_code_str += f"G:{(record.type + ' ' + record.display_name)[:60]}*"
            qr_code_str += f"H:0*"
            qr_code_str += f"I1:{record.company_id.country_id.code}*"
            base_vat_exempt = get_base_and_vat(record.amount_by_group, 'IVA 0%', record.currency_id)
            base_vat_reduced = get_base_and_vat(record.amount_by_group, 'IVA 6%', record.currency_id)
            base_vat_intermediate = get_base_and_vat(record.amount_by_group, 'IVA 13%', record.currency_id)
            base_vat_normal = get_base_and_vat(record.amount_by_group, 'IVA 23%', record.currency_id)
            if base_vat_exempt:
                qr_code_str += f"I2:{base_vat_exempt['base']}*"
            if base_vat_reduced:
                qr_code_str += f"I3:{base_vat_reduced['base']}*"
                qr_code_str += f"I4:{base_vat_reduced['vat']}*"
            if base_vat_intermediate:
                qr_code_str += f"I5:{base_vat_intermediate['base']}*"
                qr_code_str += f"I6:{base_vat_intermediate['vat']}*"
            if base_vat_normal:
                qr_code_str += f"I7:{base_vat_normal['base']}*"
                qr_code_str += f"I8:{base_vat_normal['vat']}*"
            qr_code_str += f"N:{record.amount_tax}*"
            qr_code_str += f"O:{record.amount_total}*"
            qr_code_str += f"Q:TODO*"
            qr_code_str += f"R:TODO*"

            if qr_code_str[-1] == "*":
                qr_code_str = qr_code_str[:-1]
            record.l10n_pt_qr_code_str = qr_code_str
            print(qr_code_str)
