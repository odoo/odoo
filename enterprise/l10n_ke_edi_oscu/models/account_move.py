# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import logging
import json
from datetime import datetime
from collections import defaultdict
from zoneinfo import ZoneInfo
from psycopg2.errors import LockNotAvailable

from odoo import _, api, Command, fields, models, modules, tools
from odoo.exceptions import UserError
from odoo.addons.base.models.ir_qweb_fields import Markup
from odoo.tools.float_utils import json_float_round, float_compare

_logger = logging.getLogger(__name__)

TAX_CODE_LETTERS = ['A', 'B', 'C', 'D', 'E']


def format_etims_datetime(dt):
    """ Format a UTC datetime as expected by eTIMS (only digits, Kenyan timezone). """
    return dt.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo('Africa/Nairobi')).strftime('%Y%m%d%H%M%S')


def parse_etims_datetime(dt_str):
    """ Parse a datetime string received from eTIMS into a UTC datetime. """
    return datetime.strptime(dt_str, '%Y%m%d%H%M%S').replace(tzinfo=ZoneInfo('Africa/Nairobi')).astimezone(ZoneInfo('UTC')).replace(tzinfo=None)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # === Business fields === #
    l10n_ke_payment_method_id = fields.Many2one(
        string="eTIMS Payment Method",
        comodel_name='l10n_ke_edi_oscu.code',
        domain=[('code_type', '=', '07')],
        help="Method of payment communicated to the KRA via eTIMS. This is required when confirming purchases.",
    )
    l10n_ke_reason_code_id = fields.Many2one(
        string="eTIMS Credit Note Reason",
        comodel_name='l10n_ke_edi_oscu.code',
        domain=[('code_type', '=', '32')],
        copy=False,
        help="Kenyan code for Credit Notes",
    )

    # === eTIMS Technical fields === #
    l10n_ke_oscu_confirmation_datetime = fields.Datetime(copy=False)
    l10n_ke_oscu_receipt_number = fields.Integer(string="Receipt Number", copy=False)
    l10n_ke_oscu_invoice_number = fields.Integer(string="Invoice Number", copy=False)
    l10n_ke_oscu_signature = fields.Char(string="eTIMS Signature", copy=False)
    l10n_ke_oscu_datetime = fields.Datetime(string="eTIMS Signing Time", copy=False)
    l10n_ke_oscu_internal_data = fields.Char(string="Internal Data", copy=False)
    l10n_ke_control_unit = fields.Char(string="Control Unit ID")
    l10n_ke_oscu_attachment_file = fields.Binary(copy=False, attachment=True)
    l10n_ke_oscu_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="eTIMS Attachment",
        compute=lambda self: self._compute_linked_attachment_id('l10n_ke_oscu_attachment_id', 'l10n_ke_oscu_attachment_file'),
        depends=['l10n_ke_oscu_attachment_file'],
    )
    l10n_ke_validation_message = fields.Json(compute='_compute_l10n_ke_validation_message', compute_sudo=True)

    # === Computes === #

    @api.depends('l10n_ke_oscu_invoice_number')
    def _compute_tax_totals(self):
        # EXTENDS 'account'
        super()._compute_tax_totals()
        for move in self:
            if move.l10n_ke_oscu_invoice_number and move.tax_totals:
                # Disable the recap of tax totals in company currency at the bottom right of the invoice,
                # since this info is already present in our custom tax totals grid.
                move.tax_totals['display_in_company_currency'] = False

    @api.depends('l10n_ke_oscu_attachment_id')
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        self.filtered(lambda m: m.l10n_ke_oscu_invoice_number).show_reset_to_draft_button = False

    @api.depends('invoice_date',
                 'invoice_line_ids.product_id',
                 'invoice_line_ids.product_uom_id',
                 'reversed_entry_id',
                 'l10n_ke_reason_code_id',
                 'l10n_ke_payment_method_id')
    def _compute_l10n_ke_validation_message(self):
        """ Compute the series of messages to be displayed in the banner at the header of the invoice. """
        for move in self:
            if not move.is_invoice(include_receipts=True) or move.country_code != 'KE':
                move.l10n_ke_validation_message = False
                continue

            product_lines = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
            messages = {
                **product_lines.product_id._l10n_ke_get_validation_messages(for_invoice=True),
                **product_lines.product_uom_id._l10n_ke_get_validation_messages(),
            }

            if not move.company_id.l10n_ke_oscu_is_active:
                messages['etims_configuration_warning'] = {
                    'message': _(
                        "eTIMS configuration is incomplete for company '%(company)s'. Please verify that the eTIMS Server Mode, "
                        "OSCU Configuration, and the company's eTIMS Branch Code are correctly set up to proceed.",
                        company=move.company_id.name
                    ),
                    'blocking': True,
                }
                move.l10n_ke_validation_message = messages
                continue

            if move.l10n_ke_oscu_invoice_number and not move.l10n_ke_oscu_receipt_number and not move.l10n_ke_oscu_signature:
                messages['timeout_warning'] = {
                    'message': _("The eTIMS connection timed out while sending the invoice, please try again later.")
                }

            if move.is_purchase_document(include_receipts=True) and not move.l10n_ke_payment_method_id:
                messages['no_payment_method_warning'] = {
                    'message': _("An eTIMS payment method is required when confirming a purchase. "),
                    'blocking': True,
                }

            if move.move_type == 'out_refund':
                if not move.l10n_ke_reason_code_id:
                    messages['no_reason_code_warning'] = {
                        'message': _("A KRA reason code is required when creating credit notes. "),
                        'blocking': True,
                    }
                if not move.reversed_entry_id or not (move.reversed_entry_id.l10n_ke_oscu_invoice_number and move.reversed_entry_id.l10n_ke_oscu_receipt_number):
                    messages['no_reversed_entry_warning'] = {
                        'message': _("A credit note must be linked to an invoice that has already been submitted to eTIMS."),
                        'blocking': True,
                    }

                if move.reversed_entry_id and move.reversed_entry_id.invoice_date > move.invoice_date:
                    messages['credit_date_error'] = {
                        'message': _("eTims does not accept credit notes with a date earlier than the corresponding invoice."),
                        'blocking': True,
                    }

            if product_lines.filtered(lambda line: not line.product_id):
                messages['no_product_warning'] = {
                    'message': _("Some lines are missing a product where one must be set. "),
                    'blocking': True,
                }

            lines_not_single_tax = self.env['account.move.line']
            unspsc_tax_mismatch_products = self.env['product.product']

            for line in product_lines:
                vat_taxes = line.tax_ids.filtered(lambda t: t.l10n_ke_tax_type_id)
                if len(vat_taxes) != 1 and line.product_id:
                    lines_not_single_tax |= line
                if (product_tax_type := line.product_id.unspsc_code_id.l10n_ke_tax_type_id) and product_tax_type not in vat_taxes.l10n_ke_tax_type_id:
                    unspsc_tax_mismatch_products |= line.product_id

            if lines_not_single_tax:
                messages['lines_not_single_vat_tax'] = {
                    'message': _("All invoice lines must include a tax line and exactly one VAT tax, with the KRA Tax Code properly set."),
                    'blocking': True,
                }

            if unspsc_tax_mismatch_products:
                messages['unspsc_tax_mismatch_warning'] = {
                    'message': _(
                        "There are products in use with UNSPSC codes for which the KRA has specified a "
                        "different tax rate to that in use on the line."
                    ),
                    'action_text': _("View Product(s)"),
                    'action': unspsc_tax_mismatch_products._get_records_action(name=_("View Product(s)"), context={}),
                    'blocking': False,
                }

            move.l10n_ke_validation_message = messages

    # === Sending to eTIMS: common helpers === #

    def _update_receipt_content(self, content, confirmation_datetime, invoice_date, partner):
        receipt_part = {
            'custTin': (partner.vat or '')[:11],  # Partner VAT
            'rcptPbctDt': confirmation_datetime,  # Receipt published date
            'prchrAcptcYn': 'N',  # Purchase accepted Yes/No
        }
        if partner.mobile:
            receipt_part.update({
                'custMblNo': (partner.mobile or '')[:20]  # Mobile number, not required
            })
        if partner.contact_address_inline:
            receipt_part.update({
                'adrs': (partner.contact_address_inline or '')[:200],  # Address, not required
            })
        content.update({
            'custTin': (partner.vat or '')[:11],  # Partner VAT
            'custNm': (partner.name or '')[:60],  # Partner name
            'salesSttsCd': '02',  # Transaction status code (same as pchsSttsCd)
            'salesDt': invoice_date,  # Sales date
            'prchrAcptcYn': 'Y',
            'receipt': receipt_part,
        })

    def _get_taxes_data(self, line_items):
        tax_codes = {item['code']: item['tax_rate'] for item in self.env['l10n_ke_edi_oscu.code'].search([('code_type', '=', '04')])}
        tax_rates = {f'taxRt{letter}': tax_codes.get(letter, 0) for letter in TAX_CODE_LETTERS}

        taxable_amounts = {
            f'taxblAmt{letter}': json_float_round(sum(
                item['taxblAmt'] for item in line_items if item['taxTyCd'] == letter
            ), 2) for letter in TAX_CODE_LETTERS
        }
        tax_amounts = {
            f'taxAmt{letter}': json_float_round(sum(
                item['taxAmt'] for item in line_items if item['taxTyCd'] == letter
            ), 2) for letter in TAX_CODE_LETTERS
        }

        return tax_codes, tax_rates, taxable_amounts, tax_amounts

    def _l10n_ke_oscu_json_from_move(self):
        """ Get the json content of the TrnsSalesSaveWr/TrnsPurchaseSave request from a move. """
        self.ensure_one()

        confirmation_datetime = format_etims_datetime(self.l10n_ke_oscu_confirmation_datetime)
        invoice_date = (self.invoice_date and self.invoice_date.strftime('%Y%m%d')) or ''
        original_invoice_number = (self.reversed_entry_id and self.reversed_entry_id.l10n_ke_oscu_invoice_number) or 0
        tax_details = self._prepare_invoice_aggregated_taxes()
        line_items = self._l10n_ke_oscu_get_json_from_lines(tax_details)
        tax_codes, tax_rates, taxable_amounts, tax_amounts = self._get_taxes_data(line_items)

        content = {
            'invcNo':           '',                                        # KRA Invoice Number (set at the point of sending)
            'trdInvcNo':        (self.name or '')[:50],                            # Trader system invoice number
            'orgInvcNo':        original_invoice_number,                   # Original invoice number
            'cfmDt':            confirmation_datetime,                     # Validated date
            'pmtTyCd':          self.l10n_ke_payment_method_id.code or '',  # Payment type code
            'rcptTyCd': {                                                  # Receipt code
                'out_invoice':  'S',                                       # - Sale
                'out_refund':   'R',                                       # - Credit note after sale
                'in_invoice':   'P',                                       # - Purchase
                'in_refund':    'R',                                       # - Credit note after purchase
            }[self.move_type],
            **taxable_amounts,
            **tax_amounts,
            **tax_rates,
            'totTaxblAmt':      json_float_round(tax_details['base_amount'], 2),
            'totTaxAmt':        json_float_round(tax_details['tax_amount'], 2),
            'totAmt':           json_float_round(abs(self.amount_total_signed), 2),
            'totItemCnt':       len(line_items),                           # Total Item count
            'itemList':         line_items,
            **self.company_id._l10n_ke_get_user_dict(self.create_uid, self.write_uid),
        }

        if self.is_purchase_document(include_receipts=True):
            content.update({
                'spplrTin':     (self.partner_id.vat or '')[:11],          # Supplier VAT
                'spplrNm':      (self.partner_id.name or '')[:60],         # Supplier name
                'regTyCd':      'M',                                       # Registration type code (Manual / Automatic)
                'pchsTyCd':     'N',                                       # Purchase type code (Copy / Normal / Proforma)
                'pchsSttsCd':   '02',                                      # Transaction status code (02 approved / 05 credit note generated)
                'pchsDt':       invoice_date,                              # Purchase date
                # "spplrInvcNo": None,
            })
        else:
            self._update_receipt_content(content, confirmation_datetime, invoice_date, self.partner_id)

        if self.move_type in ('out_refund', 'in_refund'):
            content.update({'rfdRsnCd': self.l10n_ke_reason_code_id.code})
        return content

    def _l10n_ke_oscu_get_json_from_lines(self, tax_details):
        """ Return the values that should be sent to eTIMS for the lines in self. """
        self.ensure_one()
        lines_values = []
        for index, line in enumerate(self.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))):
            product = line.product_id  # for ease of reference
            product_uom_qty = line.product_uom_id._compute_quantity(line.quantity, product.uom_id)

            tax, line_tax_details = next(
                (tax, line_tax_details)
                for tax, line_tax_details in tax_details['tax_details_per_record'][line]['tax_details'].items()
                if tax.l10n_ke_tax_type_id  # We only want to report VAT taxes
            )

            if line.quantity and line.discount != 100:
                # By computing the price_unit this way, we ensure that we get the price before the VAT tax, regardless of what
                # other price_include / price_exclude taxes are defined on the product.
                price_subtotal_before_discount = line_tax_details['base_amount'] / (1 - (line.discount / 100))
                price_unit = price_subtotal_before_discount / line.quantity
            else:
                price_unit = line.price_unit
                price_subtotal_before_discount = price_unit * line.quantity
            discount_amount = price_subtotal_before_discount - line_tax_details['base_amount']

            line_values = {
                'itemSeq':   index + 1,                                             # Line number
                'itemCd':    product.l10n_ke_item_code,                             # Item code as defined by us, of the form KE2BFTNE0000000000000039
                'itemClsCd': product.unspsc_code_id.code,                           # Item classification code, in this case the UNSPSC code
                'itemNm':    line.name,                                             # Item name
                'pkgUnitCd': product.l10n_ke_packaging_unit_id.code,                # Packaging code, describes the type of package used
                'pkg':       product_uom_qty / product.l10n_ke_packaging_quantity,  # Number of packages used
                'qtyUnitCd': line.product_uom_id.l10n_ke_quantity_unit_id.code,     # The UOMs as defined by the KRA, defined seperately from the UOMs on the line
                'qty':       line.quantity,
                'prc':       price_unit,
                'splyAmt':   price_subtotal_before_discount,
                'dcRt':      line.discount,
                'dcAmt':     discount_amount,
                'taxTyCd':   tax.l10n_ke_tax_type_id.code,
                'taxblAmt':  line_tax_details['base_amount'],
                'taxAmt':    line_tax_details['tax_amount'],
                'totAmt':    line_tax_details['base_amount'] + line_tax_details['tax_amount'],
            }

            fields_to_round = ('pkg', 'qty', 'prc', 'splyAmt', 'dcRt', 'dcAmt', 'taxblAmt', 'taxAmt', 'totAmt')
            for field in fields_to_round:
                line_values[field] = json_float_round(line_values[field], 2)

            if product.barcode:
                line_values.update({'bcd': product.barcode})

            lines_values.append(line_values)
        return lines_values

    def _l10n_ke_oscu_json_from_attachment(self):
        """Get the json content of the TrnsPurchaseSave request given an attachment on the move."""

        self.ensure_one()
        if not self.l10n_ke_oscu_attachment_id:
            return {}

        if not self._is_vendor_bill_json(self.l10n_ke_oscu_attachment_id.raw):
            return {}

        file_content = json.loads(self.l10n_ke_oscu_attachment_id.raw)

        # Firstly, those fields that map directly from the file to the purchase confirmation request
        content = {field: file_content[field] for field in (
            'spplrTin', 'spplrNm', 'spplrBhfId',
            'spplrInvcNo', 'pmtTyCd', 'totItemCnt',
            'taxblAmtA', 'taxRtA', 'taxAmtA',
            'taxblAmtB', 'taxRtB', 'taxAmtB',
            'taxblAmtC', 'taxRtC', 'taxAmtC',
            'taxblAmtD', 'taxRtD', 'taxAmtD',
            'taxblAmtE', 'taxRtE', 'taxAmtE',
            'totTaxblAmt', 'totTaxAmt', 'totAmt',
        )}

        confirmation_datetime = format_etims_datetime(self.l10n_ke_oscu_confirmation_datetime)
        content.update({
            'invcNo':     '',
            'orgInvcNo':   0,                                              # No original invoice
            'regTyCd':    'M',                                             # Registration type: manual
            'pchsTyCd':   'N',                                             # Purchase type: normal
            'pchsSttsCd': '02',                                            # Transaction progress: Accepted
            'pchsDt':     file_content['salesDt'],
            'cfmDt':      confirmation_datetime,                           # Validated date
            **self.company_id._l10n_ke_get_user_dict(self.create_uid, self.write_uid),
        })

        item_list = []
        for file_item in file_content['itemList']:
            item = {field: file_item[field] for field in (
                'itemSeq', 'itemClsCd', 'itemNm', 'pkgUnitCd', 'bcd', 'pkg', 'qtyUnitCd', 'qty',
                'prc', 'splyAmt', 'dcRt', 'dcAmt', 'taxblAmt', 'taxTyCd', 'taxAmt', 'totAmt',
            )}
            item.update({
                'itemCd': '',
                'spplrItemCd':    file_item['itemCd'],
                'supplrItemNm':   file_item['itemNm'],
                'spplrItemClsCd': file_item['itemClsCd'],
            })
            item_list.append(item)

        content['itemList'] = item_list
        return content

    def _l10n_ke_get_invoice_sequence(self):
        """ Returns the KRA invoice sequence for this invoice (company and move_type dependent), creating it if needed. """
        self.ensure_one()

        sequence_code = 'l10n.ke.oscu.sale.sequence' if self.is_sale_document(include_receipts=True) else 'l10n.ke.oscu.purchase.sequence'

        if not (sequence := self.env['ir.sequence'].search([
            ('code', '=', sequence_code),
            ('company_id', '=', self.company_id.id),
        ])):
            sequence_name = 'eTIMS Customer Invoice Number' if self.is_sale_document(include_receipts=True) else 'eTIMS Vendor Bill Number'
            return self.env['ir.sequence'].create({
                'name': sequence_name,
                'implementation': 'no_gap',
                'company_id': self.company_id.id,
                'code': sequence_code,
            })
        return sequence

    # === Sending to eTIMS: invoices and credit notes === #

    def _post(self, soft=True):
        """ Perform checks related to credit notes and set the confirmation datetime

        Unfortunately the KRA requires that this is performed here, as there is no validation of this
        kind in their system. The purpose of these credit note checks is to confirm that neither the
        quantities nor the monetary amounts exceed their values on the source customer invoice.
        """
        # EXTENDS 'account'
        for move in self.filtered(lambda move: move.country_code == 'KE' and move.reversed_entry_id):
            original_move = move.reversed_entry_id
            reversals = original_move._get_reconciled_invoices().filtered(lambda move: move.move_type == 'out_refund')

            # Unless all the invoices / credit notes are made in the same currency, we can't conveniently
            # check that the credit notes don't exceed the invoices (due to exchange rate differences),
            # so we skip this check.
            if len(set(original_move.mapped('currency_id') + reversals.mapped('currency_id'))) != 1:
                continue

            original_quantities = defaultdict(lambda: 0)
            reverse_quantities = defaultdict(lambda: 0)

            for line in original_move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                original_quantities[line.product_id] += line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)
            for line in reversals.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                reverse_quantities[line.product_id] += line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)

            exceeding_quantities = []
            for product, quantity in reverse_quantities.items():
                if product not in original_quantities:
                    exceeding_quantities.append(_("'%s' is not present on the original invoice.", product.name))
                elif (excess := quantity - original_quantities[product]) > 0:
                    exceeding_quantities.append(
                        _(
                            "'%(product_name)s' exceeds quantity on original invoice by %(excess)f %(uom_name)s",
                            product_name=product.name,
                            excess=excess,
                            uom_name=product.uom_id.name
                        )
                    )

            if exceeding_quantities:
                if len(reversals) > 1:
                    raise UserError(_(
                        "This credit note in conjunction with %(other_credit_notes)s has items of a quantity exceeding "
                        "that of the original customer invoice %(original_invoice)s. Please correct the quantity of "
                        "these lines before confirming:\n%(lines_to_correct)s",
                        other_credit_notes=', '.join(
                            rec.name or f"the credit note with ID {rec.id}"
                            for rec in (reversals - move)
                        ),
                        original_invoice=original_move.name,
                        lines_to_correct='\n'.join(exceeding_quantities),
                    ))
                raise UserError(_(
                    "This credit note has items of a quantity exceeding that of the original "
                    "customer invoice %(original_invoice)s. Please correct the quantity of these lines before "
                    "confirming:\n%(lines_to_correct)s",
                    original_invoice=original_move.name,
                    lines_to_correct='\n'.join(exceeding_quantities),
                ))

            credit_note_total = abs(sum(move.amount_total_in_currency_signed for move in reversals))
            excess = abs(credit_note_total) - abs(original_move.amount_total_in_currency_signed)

            if float_compare(excess, 0, precision_digits=2) > 0:
                if len(reversals) > 1:
                    raise UserError(_(
                        "This credit note in conjunction with %(other_credit_notes)s exceeds the amount on the "
                        "original customer invoice %(original_invoice)s. "
                        "Please adjust this credit note to a total value equal to or less than %(total_value)d before confirming.",
                        other_credit_notes=', '.join(
                            rec.name or f"the credit note with ID {rec.id}"
                            for rec in (reversals - move)
                        ),
                        original_invoice=original_move.name,
                        total_value=abs(move.amount_total_in_currency_signed) - excess,
                    ))
                raise UserError(_(
                    "This credit note exceeds the amount of the original customer invoice %(original_invoice)s. "
                    "Please adjust this credit note to a total value equal to or less than %(total_value)d before confirming.",
                    original_invoice=original_move.name,
                    total_value=abs(move.amount_total_in_currency_signed) - excess,
                ))

        self\
            .filtered(lambda m: not m.l10n_ke_oscu_confirmation_datetime)\
            .with_context(skip_is_manually_modified=True)\
            .l10n_ke_oscu_confirmation_datetime = fields.Datetime.now()

        return super()._post(soft)

    def _get_fields_to_detach(self):
        # EXTENDS account
        fields_list = super()._get_fields_to_detach()
        fields_list.append('l10n_ke_oscu_attachment_file')
        return fields_list

    def _l10n_ke_register_products(self):
        """ Register products with eTIMS before sending invoices or vendor bills. """
        for move in self:
            products_to_register = move.invoice_line_ids.product_id.filtered(
                lambda p: p and not p.l10n_ke_item_code
            )

            for product in products_to_register:
                error, _content = product._l10n_ke_oscu_save_item(company=move.company_id)
                if error:
                    _logger.warning(
                        "Failed to register product '%s' (ID: %d) for invoice %s: [%s] %s",
                        product.name, product.id, move.name, error.get('code', 'Unknown'), error.get('message', 'Unknown error')
                    )

    def _l10n_ke_oscu_send_customer_invoice(self):
        self.env['res.company']._with_locked_records(self)
        self._l10n_ke_register_products()
        company = self.company_id

        if self.l10n_ke_oscu_invoice_number:
            error, data = self._l10n_ke_oscu_fetch_invoice_details()
            if not error:
                data = data['receipt']
                date_str = data['sdcDateTime'].split('.')[0]  # Remove microseconds
                signing_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=ZoneInfo('Africa/Nairobi')).astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
                self.write({
                    'l10n_ke_oscu_receipt_number': data['curRcptNo'],
                    'l10n_ke_oscu_signature': data['rcptSign'],
                    'l10n_ke_oscu_datetime': signing_date,
                    'l10n_ke_oscu_internal_data': data['intrlData'],
                    'l10n_ke_control_unit': company.l10n_ke_control_unit,
                })
                return data, error
            elif error['code'] == 'TIM':
                return data, error

        if self.move_type == 'out_refund' and company.l10n_ke_server_mode != 'demo':
            error, data = self.reversed_entry_id._l10n_ke_oscu_fetch_invoice_details()
            if error:
                return data, error
            # Normalize None to False to avoid None != False when customer had no PIN on invoice
            invoice_customer_pin = data['custTin'] or False
            if invoice_customer_pin != self.partner_id.vat:
                error = {
                    'code': 'WRONG_PIN',
                    'message': _(
                        "The customer PIN on the credit note differs from the PIN on the original invoice submitted to the KRA.\n"
                        "The KRA only accepts credit notes with matching PINs.\n"
                        "Customer PIN on the invoice: %s", invoice_customer_pin or ''
                    ),
                }
                return {}, error

        content = self._l10n_ke_oscu_json_from_move()

        try:
            self.l10n_ke_oscu_invoice_number = content['invcNo'] = self.l10n_ke_oscu_invoice_number or self._l10n_ke_get_invoice_sequence().next_by_id()
        except LockNotAvailable:
            raise UserError(_("Another user is already sending this invoice.")) from None

        error, data, _date = company._l10n_ke_call_etims('saveTrnsSalesOsdc', content)
        if not error:
            self.write({
                'l10n_ke_oscu_receipt_number': data['curRcptNo'],
                'l10n_ke_oscu_signature': data['rcptSign'],
                'l10n_ke_oscu_datetime': parse_etims_datetime(data['sdcDateTime']),
                'l10n_ke_oscu_internal_data': data['intrlData'],
                'l10n_ke_control_unit': company.l10n_ke_control_unit,
            })
        elif error['code'] != 'TIM':
            # In order not to rollback, but just to avoid consuming the invoice number
            self._l10n_ke_get_invoice_sequence().number_next -= 1
            self.l10n_ke_oscu_invoice_number = False
        return content, error

    # === Sending to eTIMS: vendor bills === #

    def action_l10n_ke_oscu_confirm_vendor_bill(self):
        """Send vendor bill information to the KRA in order to confirm that it has been accepted

        Vendor bills can be received from the OSCU or created locally. When confirming vendor bills
        received from the KRA, we can use the information from the attachment used to generate the
        invoice in the first place to create the request. If the invoice is created locally,
        generate the request using just the fields on the vendor bill.
        """
        for move in self:
            if (blocking := [msg for msg in (move.l10n_ke_validation_message or {}).values() if msg.get('blocking')]):
                raise UserError(_("Please resolve these issues first.\n %s",
                                  '\n'.join([f"- {msg['message']}" for msg in blocking])))
            move._l10n_ke_register_products()
            company = move.company_id

            if move.l10n_ke_oscu_attachment_id:
                content = {
                    **move._l10n_ke_oscu_json_from_attachment(),
                    'rcptTyCd': {'in_invoice': 'P', 'in_refund': 'R'}.get(move.move_type),
                    'regTyCd': 'A',
                }
                if not content['pmtTyCd']:
                    content['pmtTyCd'] = move.l10n_ke_payment_method_id.code
            else:
                content = move._l10n_ke_oscu_json_from_move()

            try:
                content['invcNo'] = move._l10n_ke_get_invoice_sequence().next_by_id()
            except LockNotAvailable:
                raise UserError(_("Another user is already sending this vendor bill.")) from None

            error, _data, _date = company._l10n_ke_call_etims('insertTrnsPurchase', content)

            if error:
                raise UserError(error['message'])

            move.l10n_ke_oscu_invoice_number = content['invcNo']
            move.message_post(body=_("Purchase confirmed on eTIMS."))

    # === Fetching from eTIMS: Invoice Details === #
    def _l10n_ke_oscu_fetch_invoice_details(self):
        """
        Fetch invoice details from the KRA eTIMS system by its invoice number.

        :param int invoice_number: the invoice number to fetch from the KRA.
        """
        self.ensure_one()
        company = self.company_id
        error, data, _date = company._l10n_ke_call_etims(
            'selectInvoiceDetails',
            {'invcNo': self.l10n_ke_oscu_invoice_number}
        )
        if error:
            if error['code'] == '001':
                _logger.warning("There is no invoice with number %s on the OSCU for %s.", self.l10n_ke_oscu_invoice_number, company.name)
            else:
                _logger.error("Error retrieving invoice details from the OSCU: %s: %s", error['code'], error['message'])
            return error, None
        return [], data['salesList'][0] if data['salesList'] else None

    # === Fetching from eTIMS: vendor bills === #

    def _l10n_ke_oscu_fetch_purchases(self, companies):
        """ Retrieve vendor bills from the KRA

        :param recordset companies: recordset containing comanies for which purchases should be
            fetched from the KRA.
        :returns: recordset of the fetched invoices
        """
        moves = self
        for company in companies:
            error, data, _date = company._l10n_ke_call_etims(
                'selectTrnsPurchaseSalesList',
                {'lastReqDt': format_etims_datetime(company.l10n_ke_oscu_last_fetch_purchase_date or datetime(2018, 1, 1))}
            )
            if error:
                if error['code'] == '001':
                    _logger.warning("There are no new vendor bills on the OSCU for %s.", company.name)
                else:
                    _logger.error("Error retrieving purchases from the OSCU: %s: %s", error['code'], error['message'])
                continue

            for purchase in data['saleList']:
                filename = f"{purchase['spplrSdcId']}_{purchase['spplrInvcNo']}.json"
                if self.env['ir.attachment'].search_count([
                    ('name', '=', filename),
                    ('res_model', '=', 'account.move'),
                    ('res_field', '=', 'l10n_ke_oscu_attachment_file'),
                ], limit=1):
                    _logger.warning("Vendor bill already exists: %s", filename)
                    continue

                move_type = {
                    'S': 'in_invoice',
                    'R': 'in_refund',
                }.get(purchase['rcptTyCd'], 'in_invoice')
                move = self.sudo().with_company(company).with_context(default_move_type=move_type).create({})
                attachment = self.sudo().env['ir.attachment'].create({
                    'name': filename,
                    'raw': json.dumps(purchase, indent=4),
                    'type': 'binary',
                    'res_model': 'account.move',
                    'res_id': move.id,
                    'res_field': 'l10n_ke_oscu_attachment_file',
                })
                move.invalidate_recordset(fnames=['l10n_ke_oscu_attachment_id', 'l10n_ke_oscu_attachment_file'])
                move.with_context(
                    account_predictive_bills_disable_prediction=True,
                    no_new_invoice=True,
                ).message_post(attachment_ids=attachment.ids)
                moves |= move

            company.l10n_ke_oscu_last_fetch_purchase_date = fields.Datetime.now()

        for move in moves:
            move._extend_with_attachments(move.l10n_ke_oscu_attachment_id, new=True)
            # Avoid losing all our progress if the cron times-out
            if not tools.config['test_enable'] and not modules.module.current_test:
                self.env.cr.commit()

        return moves

    def _cron_l10n_ke_oscu_fetch_purchases(self):
        """ Fetch purchases for all the relevant companies """
        companies = self.env['res.company'].search([('l10n_ke_oscu_is_active', '=', True)])
        moves = self._l10n_ke_oscu_fetch_purchases(companies)
        _logger.info(
            "KE EDI cron retrieved purchases for %s companies, and created %s vendor bills.",
            len(moves.company_id),
            len(moves),
        )

    @api.model
    def _is_vendor_bill_json(self, file_content):
        """ Determine whether the given file content is a vendor bill JSON retrieved from eTIMS. """
        with contextlib.suppress(json.JSONDecodeError, UnicodeDecodeError):
            content = json.loads(file_content)
            return all(key in content for key in ('spplrTin', 'spplrNm', 'spplrBhfId', 'spplrInvcNo'))

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        if file_data['type'] == 'binary' and self._is_vendor_bill_json(file_data['content']):
            return self._l10n_ke_oscu_import_invoice
        return super()._get_edi_decoder(file_data, new=new)

    def _l10n_ke_oscu_import_invoice(self, invoice, data, is_new):
        """ Decodes the json content from eTIMS into an Odoo move.

        This method is passed as the EDI decoder in the case where the file is recognised as an OSCU
        JSON representation of a vendor bill.

        :param dictionary data: the dictionary with the content to be imported
        :param boolean is_new:  whether the vendor bill is newly created or to be updated
        :returns:               the imported vendor bill
        """
        with self._get_edi_creation() as self:
            content = json.loads(data['content'])
            message_to_log = []

            self.move_type = {
                'S': 'in_invoice',
                'R': 'in_refund',
            }.get(content['rcptTyCd'], 'in_invoice')

            branch = self.env['res.partner'].search([('vat', '=ilike', content['spplrTin']),
                                                    ('l10n_ke_branch_code', '=', content['spplrBhfId'])], limit=1)
            if branch:
                self.partner_id = branch
            else:
                self.partner_id = self.env['res.partner'].create({
                    'name': content['spplrNm'],
                    'vat': content['spplrTin'],
                    'l10n_ke_branch_code': content['spplrBhfId'],
                })
                message_to_log.extend((
                    _(
                        "A vendor with a matching Tax ID and Branch ID was not found. "
                        "One with the corresponding details was created."
                    ),
                    "",
                ))

            self.invoice_date = datetime.strptime(content['salesDt'], '%Y%m%d').date()
            self.l10n_ke_control_unit = content['spplrSdcId']
            uom_codes = [line['qtyUnitCd'] for line in content['itemList']]
            uom_map = {
                uom.l10n_ke_quantity_unit_id.code: uom
                for uom in self.env['uom.uom'].search([('l10n_ke_quantity_unit_id.code', 'in', uom_codes)])
            }
            tax_rate_map = {code: content[f'taxRt{code}'] for code in TAX_CODE_LETTERS}

            invoice_lines = []
            for item in content['itemList']:
                line = {}
                product, msg = self.env['product.product']._l10n_ke_oscu_find_product_from_json(
                    {k: item[k] for k in ('itemNm', 'bcd', 'itemClsCd')}
                )
                if msg:
                    message_to_log.append(msg)
                line['product_id'] = product and product.id or None
                line['tax_ids'] = self.env['account.tax'].search([
                    ('type_tax_use', '=', 'purchase'),
                    *self.env['account.tax']._check_company_domain(self.company_id),
                    ('l10n_ke_tax_type_id.code', '=', item['taxTyCd']),
                    ('amount', '=', tax_rate_map[item['taxTyCd']]),  # in handy if tax rates would change
                    ('amount_type', '=', 'percent'),
                ], limit=1).ids

                # If we don't already have a matching UoM from the product
                line['product_uom_id'] = uom_map.get(item['qtyUnitCd'], self.env['uom.uom']).id or (product and product.uom_id.id) or self.env.ref('uom.product_uom_unit').id
                line['name'] = item['itemNm']
                line['quantity'] = item['qty']
                line['price_unit'] = item['prc']
                line['discount'] = item['dcRt']
                line['sequence'] = item['itemSeq'] * 10
                invoice_lines.append(Command.create(line))

            self.invoice_line_ids = invoice_lines
            message = Markup("<br/>").join(message_to_log)
            # for message in message_to_log:
            self.sudo().message_post(body=message)
            return True

    # === Report generation === #
    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.l10n_ke_oscu_invoice_number:
            return 'l10n_ke_edi_oscu.report_invoice_document'
        return super()._get_name_invoice_report()

    @api.model
    def _l10n_ke_hyphenate_invoice_field(self, to_hyphenate, hyphenate_by=4):
        """Hyphenates a string by a regular interval

        :param str to_hyphenate: string to be hyphenated (e.g. 'abcdefghijklmnop' becomes 'abcd-efgh-ijkl-mnop')
        :param int hyphenate_by: the regular interval at which to add a hyphen
        """
        return '-'.join(to_hyphenate[idx: idx + hyphenate_by] for idx in range(0, len(to_hyphenate), hyphenate_by))

    def _l10n_ke_oscu_get_receipt_url(self):
        self.ensure_one()
        domain = 'etims-sbx' if self.company_id.l10n_ke_server_mode == 'test' else 'etims'
        data = f'{self.company_id.vat}{self.company_id.l10n_ke_branch_code}{self.l10n_ke_oscu_signature}'
        return f'https://{domain}.kra.go.ke/common/link/etims/receipt/indexEtimsReceiptData?Data={data}'

    def _refunds_origin_required(self):
        if self.country_code == 'KE':
            return True
        return super()._refunds_origin_required()
