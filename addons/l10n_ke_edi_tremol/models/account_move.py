# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import json
import re
from datetime import datetime

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ke_cu_datetime = fields.Datetime(string='CU Signing Date and Time', copy=False)
    l10n_ke_cu_serial_number = fields.Char(string='CU Serial Number', copy=False)
    l10n_ke_cu_invoice_number = fields.Char(string='CU Invoice Number', copy=False)
    l10n_ke_cu_qrcode = fields.Char(string='CU QR Code', copy=False)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _l10n_ke_fmt(self, string, length, ljust=True):
        """ Function for common formatting behaviour

        :param string: string to be formatted/encoded
        :param length: integer length to justify (if enabled), and then truncate the string to
        :param ljust:  boolean representing whether the string should be justified
        :returns:      byte-string justified/truncated, with all non-alphanumeric characters removed
        """
        if not string:
            string = ''
        return re.sub('[^A-Za-z0-9 ]+', '', str(string)).encode('cp1251').ljust(length if ljust else 0)[:length]

    # -------------------------------------------------------------------------
    # CHECKS
    # -------------------------------------------------------------------------

    def _l10n_ke_validate_move(self):
        """ Returns list of errors related to misconfigurations per move

        Find misconfigurations on the move, the lines of the move, and the
        taxes on those lines that would result in rejection by the KRA.
        """
        errors = []
        for move in self:
            move_errors = []
            if move.country_code != 'KE':
                move_errors.append(_("This invoice is not a Kenyan invoice and therefore can not be sent to the device."))

            if move.company_id.currency_id != self.env.ref('base.KES'):
                move_errors.append(_("This invoice's company currency is not in Kenyan Shillings, conversion to KES is not possible."))

            if move.state != 'posted':
                move_errors.append(_("This invoice/credit note has not been posted. Please confirm it to continue."))

            if move.move_type not in ('out_refund', 'out_invoice'):
                move_errors.append(_("The document being sent should be an invoice or credit note."))

            if any([move.l10n_ke_cu_invoice_number, move.l10n_ke_cu_serial_number, move.l10n_ke_cu_qrcode, move.l10n_ke_cu_datetime]):
                move_errors.append(_("The document already has details related to the fiscal device. Please make sure that the invoice has not already been sent."))

            # The credit note should refer to the control unit number (receipt number) of the original
            # invoice to which it relates.
            if move.move_type == 'out_refund' and not move.reversed_entry_id.l10n_ke_cu_invoice_number:
                move_errors.append(_("This credit note must reference the previous invoice, and this previous invoice must have already been submitted."))

            for line in move.invoice_line_ids.filtered(lambda l: not l.display_type):
                if not line.tax_ids or len(line.tax_ids) > 1:
                    move_errors.append(_("On line %s, you must select one and only one tax.", line.name))
                else:
                    if line.tax_ids.amount == 0 and not (line.product_id and line.product_id.l10n_ke_hsn_code and line.product_id.l10n_ke_hsn_name):
                        move_errors.append(_("On line %s, a product with a HS Code and HS Name must be selected, since the tax is 0%% or exempt.", line.name))

            for tax in move.invoice_line_ids.tax_ids:
                if tax.amount not in (16, 8, 0):
                    move_errors.append(_("Tax '%s' is used, but only taxes of 16%%, 8%%, 0%% or Exempt can be sent. Please reconfigure or change the tax.", tax.name))

            if move_errors:
                errors.append((move.name, move_errors))

        return errors

    # -------------------------------------------------------------------------
    # SERIALISERS
    # -------------------------------------------------------------------------

    def _l10n_ke_cu_open_invoice_message(self):
        """ Serialise the required fields for opening an invoice

        :returns: a list containing one byte-string representing the <CMD> and
                  <DATA> of the message sent to the fiscal device.
        """
        headquarter_address = (self.commercial_partner_id.street or '') + (self.commercial_partner_id.street2 or '')
        customer_address = (self.partner_id.street or '') + (self.partner_id.street2 or '')
        postcode_and_city = (self.partner_id.zip or '') + '' +  (self.partner_id.city or '')
        vat = (self.commercial_partner_id.vat or '').strip() if self.commercial_partner_id.country_id.code == 'KE' else ''
        invoice_elements = [
            b'1',                                                   # Reserved - 1 symbol with value '1'
            b'     0',                                              # Reserved - 6 symbols with value ‘     0’
            b'0',                                                   # Reserved - 1 symbol with value '0'
            b'1' if self.move_type == 'out_invoice' else b'A',      # 1 symbol with value '1' (new invoice), 'A' (credit note), or '@' (debit note)
            self._l10n_ke_fmt(self.commercial_partner_id.name, 30), # 30 symbols for Company name
            self._l10n_ke_fmt(vat, 14),                             # 14 Symbols for the client PIN number
            self._l10n_ke_fmt(headquarter_address, 30),             # 30 Symbols for customer headquarters
            self._l10n_ke_fmt(customer_address, 30),                # 30 Symbols for the address
            self._l10n_ke_fmt(postcode_and_city, 30),               # 30 symbols for the customer post code and city
            self._l10n_ke_fmt('', 30),                              # 30 symbols for the exemption number
        ]
        if self.move_type == 'out_refund':
            invoice_elements.append(self._l10n_ke_fmt(self.reversed_entry_id.l10n_ke_cu_invoice_number, 19)), # 19 symbols for related invoice number
        invoice_elements.append(re.sub('[^A-Za-z0-9 ]+', '', self.name)[-15:].ljust(15).encode('cp1251'))     # 15 symbols for trader system invoice number

        # Command: Open fiscal record (0x30)
        return [b'\x30' + b';'.join(invoice_elements)]

    def _l10n_ke_cu_lines_messages(self):
        """ Serialise the data of each line on the invoice

        This function transforms the lines in order to handle the differences
        between the KRA expected data and the lines in odoo.

        If a discount line (as a negative line) has been added to the invoice
        lines, find a suitable line/lines to distribute the discount accross

        :returns: List of byte-strings representing each command <CMD> and the
                  <DATA> of the line, which will be sent to the fiscal device
                  in order to add a line to the opened invoice.
        """
        def is_discount_line(line):
            return line.price_subtotal < 0.0

        def is_candidate(discount_line, other_line):
            """ If the of one line match those of the discount line, the discount can be distributed accross that line """
            discount_taxes = discount_line.tax_ids.flatten_taxes_hierarchy()
            other_line_taxes = other_line.tax_ids.flatten_taxes_hierarchy()
            return set(discount_taxes.ids) == set(other_line_taxes.ids)

        lines = self.invoice_line_ids.filtered(lambda l: not l.display_type and l.quantity and l.price_total)

        # The device expects all monetary values in Kenyan Shillings
        if self.currency_id == self.company_id.currency_id:
            currency_rate = 1
        # In the case of a refund, use the currency rate of the original invoice
        elif self.move_type == 'out_refund' and self.reversed_entry_id:
            currency_rate = abs(self.reversed_entry_id.amount_total_signed / self.reversed_entry_id.amount_total)
        else:
            currency_rate = abs(self.amount_total_signed / self.amount_total)

        discount_dict = {line.id: line.discount for line in lines if line.price_total > 0}
        for line in lines:
            if not is_discount_line(line):
                continue
            # Search for non-discount lines
            candidate_vals_list = [l for l in lines if not is_discount_line(l) and is_candidate(l, line)]
            candidate_vals_list = sorted(candidate_vals_list, key=lambda x: x.price_unit * x.quantity, reverse=True)
            line_to_discount = abs(line.price_unit * line.quantity)
            for candidate in candidate_vals_list:
                still_to_discount = abs(candidate.price_unit * candidate.quantity * (100.0 - discount_dict[candidate.id]) / 100.0)
                if line_to_discount >= still_to_discount:
                    discount_dict[candidate.id] = 100.0
                    line_to_discount -= still_to_discount
                else:
                    rest_to_discount = abs((line_to_discount / (candidate.price_unit * candidate.quantity)) * 100.0)
                    discount_dict[candidate.id] += rest_to_discount
                    break

        vat_class = {16.0: 'A', 8.0: 'B'}
        msgs = []
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type and l.quantity and l.price_total > 0 and not discount_dict.get(l.id) >= 100):
            # Here we use the original discount of the line, since it the distributed discount has not been applied in the price_total
            price = round(line.price_total / abs(line.quantity) * 100 / (100 - line.discount), 2) * currency_rate
            percentage = line.tax_ids[0].amount

            # Letter to classify tax, 0% taxes are handled conditionally, as the tax can be zero-rated or exempt
            letter = ''
            if percentage in vat_class:
                letter = vat_class[percentage]
            else:
                report_line_ids = line.tax_ids.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'base').tag_ids.tax_report_line_ids.ids
                try:
                    exempt_report_line = self.env.ref('l10n_ke.tax_report_line_exempt_sales_base')
                except ValueError:
                    raise UserError(_("Tax exempt report line cannot be found, please update the l10n_ke module."))
                letter = 'E' if exempt_report_line.id in report_line_ids else 'C'

            uom = line.product_uom_id and line.product_uom_id.name or ''
            hscode = re.sub('[^0-9.]+', '', line.product_id.l10n_ke_hsn_code)[:10].ljust(10).encode('cp1251') if letter not in ('A', 'B') else b''.ljust(10)
            hsname = self._l10n_ke_fmt(line.product_id.l10n_ke_hsn_name, 20) if letter not in ('A', 'B') else b''.ljust(20)
            line_data = b';'.join([
                self._l10n_ke_fmt(line.name, 36),               # 36 symbols for the article's name
                self._l10n_ke_fmt(letter, 1),                   # 1 symbol for article's vat class ('A', 'B', 'C', 'D', or 'E')
                str(price)[:13].encode('cp1251'),               # 1 to 13 symbols for article's price
                self._l10n_ke_fmt(uom, 3),                      # 3 symbols for unit of measure
                hscode,                                         # 10 symbols for HS code in the format xxxx.xx.xx (can be empty)
                hsname,                                         # 20 symbols for the HS name (can be empty)
                str(percentage).encode('cp1251')[:5]            # up to 5 symbols for vat rate
            ])
            # 1 to 10 symbols for quantity
            line_data += b'*' + str(abs(line.quantity)).encode('cp1251')[:10]
            if discount_dict.get(line.id):
                # 1 to 7 symbols for percentage of discount/addition
                discount_sign = b'-' if discount_dict[line.id] > 0 else b'+'
                discount = discount_sign + str(abs(discount_dict[line.id])).encode('cp1251')[:6]
                line_data += b',' + discount + b'%'

            # Command: Sale of article (0x31)
            msgs += [b'\x31' + line_data]
        return msgs

    def _l10n_ke_get_cu_messages(self):
        """ Composes a list of all the command and data parts of the messages
            required for the fiscal device to open an invoice, add lines and
            subsequently close it.
        """
        self.ensure_one()
        msgs = self._l10n_ke_cu_open_invoice_message()
        msgs += self._l10n_ke_cu_lines_messages()
        # Command: Close fiscal reciept (0x38)
        msgs += [b'\x38']
        # Command: Read date and time (0x68)
        msgs += [b'\x68']
        return msgs

    # -------------------------------------------------------------------------
    # POST COMMANDS / RECEIVE DATA
    # -------------------------------------------------------------------------

    def l10n_ke_action_cu_post(self):
        """ Returns the client action descriptor dictionary for sending the
            invoice(s) to the fiscal device.
        """
        # Check the configuration of the invoice
        errors = self._l10n_ke_validate_move()
        if errors:
            error_msg = ""
            for move, error_list in errors:
                error_list = '\n'.join(error_list)
                error_msg += _("Invalid invoice configuration on %s:\n%s\n\n", move, error_list)
            raise UserError(error_msg)
        return {
            'type': 'ir.actions.client',
            'tag': 'post_send',
            'params': {
                'invoices': {
                    move.id: {
                        'messages': json.dumps([msg.decode('cp1251') for msg in move._l10n_ke_get_cu_messages()]),
                        'proxy_address': move.company_id.l10n_ke_cu_proxy_address,
                        'company_vat': move.company_id.vat
                    } for move in self
                }
            }
        }

    def l10n_ke_cu_response(self, response):
        """ Set the fields related to the fiscal device on the invoice.

        This is intended to be utilized by an RPC call from the javascript
        client action.
        """
        move = self.browse(int(response['move_id']))
        replies = [msg for msg in response['replies']]
        move.update({
            'l10n_ke_cu_serial_number': response['serial_number'],
            'l10n_ke_cu_invoice_number': replies[-2].split(';')[0],
            'l10n_ke_cu_qrcode': replies[-2].split(';')[1].strip(),
            'l10n_ke_cu_datetime': datetime.strptime(replies[-1], '%d-%m-%Y %H:%M'),
        })
