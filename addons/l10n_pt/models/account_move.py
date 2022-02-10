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

            company_vat_not_ok = not self.company_id.vat or not re.match("PT([0-9]{9})+|([^^]+ [0-9/]+)", record.company_id.vat)
            partner_country_not_ok = not record.partner_id.country_id
            record_type_not_ok = record.type not in {'out_invoice', 'out_refund', 'out_receipt'}

            if company_vat_not_ok or partner_country_not_ok or record_type_not_ok:
                error_msg = _("Some fields required for the generation of the document are missing or invalid. Please verify them:\n")
                error_msg += _('The `VAT` of your company should be defined and match the following format: PT123456789\n') if company_vat_not_ok else ""
                error_msg += _('The `country of the customer should be defined.\n') if partner_country_not_ok else ""
                error_msg += _('The type of document should either be an invoice, a credit note, or a receipt\n') if record_type_not_ok else ""
                raise UserError(error_msg)

    def preview_invoice(self):
        self.check_necessary_fields()
        return super().preview_invoice()

    def action_invoice_sent(self):
        self.check_necessary_fields()
        return super().action_invoice_sent()

    @api.depends('partner_id', 'currency_id', 'date', 'type', 'display_name', 'amount_by_group', 'amount_total',
                 'amount_untaxed', 'company_id', 'company_id.vat', 'company_id.country_id', 'partner_id.country_id')
    def _compute_qr_code_str(self):
        """ Generate the informational QR code for Portugal invoicing.
        E.g.: A:509445535*B:123456823*C:BE*D:FT*E:N*F:20220103*G:FT 01P2022/1*H:0*I1:PT*I7:325.20*I8:74.80*N:74.80*O:400.00*P:0.00*Q:P0FE*R:2230
        """

        def convert_to_eur(amount, account_move):
            """Convert amount to EUR based on the rate of a given account_move's date"""
            pt_currency = self.env.ref('base.EUR')
            return account_move.currency_id._convert(amount, pt_currency, account_move.company_id, account_move.date)

        def format_amount(amount):
            """Format amount to 2 decimals as per SAF-T (PT) requirements"""
            return float_repr(amount, 2)

        def get_base_and_vat(account_move, vat_name):
            """Returns the base and value tax for each type of tax"""
            vat_names = [line[0] for line in account_move.amount_by_group]
            vat_values = [line[1] for line in account_move.amount_by_group]
            vat_bases = [line[2] for line in account_move.amount_by_group]
            if vat_name not in vat_names:
                return False
            index = vat_names.index(vat_name)
            return {'base': convert_to_eur(vat_bases[index], account_move),
                    'vat': convert_to_eur(vat_values[index], account_move)}

        for move in self:  # record is of type account.move
            if move.company_id.country_id.code != "PT":
                move.l10n_pt_qr_code_str = ""
                continue

            qr_code_str = ""
            qr_code_str += f"A:{move.company_id.vat[2:]}*"
            qr_code_str += f"B:{move.partner_id.vat or '999999990'}*"
            qr_code_str += f"C:{move.partner_id.country_id.code}*"
            invoice_type_map = {
                "out_invoice": "FT",
                "out_refund": "NC",
                "out_receipt": "FR",
            }
            qr_code_str += f"D:{invoice_type_map[move.type]}*"
            qr_code_str += f"E:N*"
            qr_code_str += f"F:{format_date(self.env, move.date, date_format='yyyyMMdd')}*"
            qr_code_str += f"G:{(move.type + ' ' + move.name)[:60]}*"
            qr_code_str += f"H:0*"
            qr_code_str += f"I1:{move.company_id.country_id.code}*"

            amount_tax = 0.0
            amount_total = 0.0

            base_vat_exempt = get_base_and_vat(move, 'IVA 0%')
            if base_vat_exempt:
                qr_code_str += f"I2:{format_amount(base_vat_exempt['base'])}*"
                amount_total += base_vat_exempt['base']

            base_vat_reduced = get_base_and_vat(move, 'IVA 6%')
            if base_vat_reduced:
                qr_code_str += f"I3:{format_amount(base_vat_reduced['base'])}*"
                qr_code_str += f"I4:{format_amount(base_vat_reduced['vat'])}*"
                amount_total += base_vat_reduced['base'] + base_vat_reduced['vat']
                amount_tax += base_vat_reduced['vat']

            base_vat_intermediate = get_base_and_vat(move, 'IVA 13%')
            if base_vat_intermediate:
                qr_code_str += f"I5:{format_amount(base_vat_intermediate['base'])}*"
                qr_code_str += f"I6:{format_amount(base_vat_intermediate['vat'])}*"
                amount_total += base_vat_intermediate['base'] + base_vat_intermediate['vat']
                amount_tax += base_vat_intermediate['vat']

            base_vat_normal = get_base_and_vat(move, 'IVA 23%')
            if base_vat_normal:
                qr_code_str += f"I7:{format_amount(base_vat_normal['base'])}*"
                qr_code_str += f"I8:{format_amount(base_vat_normal['vat'])}*"
                amount_total += base_vat_normal['base'] + base_vat_normal['vat']
                amount_tax += base_vat_normal['vat']

            qr_code_str += f"N:{format_amount(amount_tax)}*"
            qr_code_str += f"O:{format_amount(amount_total)}*"
            qr_code_str += f"Q:TODO*"
            qr_code_str += f"R:0*"  # TODO: Fill Certifiate number

            if qr_code_str[-1] == "*":
                qr_code_str = qr_code_str[:-1]
            move.l10n_pt_qr_code_str = qr_code_str
