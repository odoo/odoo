# -*- coding: utf-8 -*-
import base64
from collections import defaultdict

import werkzeug
import werkzeug.exceptions
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.image import image_data_uri


class ResPartnerBank(models.Model):
    _name = 'res.partner.bank'
    _inherit = ['res.partner.bank', 'mail.thread', 'mail.activity.mixin']

    journal_id = fields.One2many(
        'account.journal', 'bank_account_id', domain=[('type', '=', 'bank')], string='Account Journal', readonly=True,
        help="The accounting journal corresponding to this bank account.")

    # Add tracking to the base fields
    bank_id = fields.Many2one(tracking=True)
    active = fields.Boolean(tracking=True)
    acc_number = fields.Char(tracking=True)
    acc_holder_name = fields.Char(tracking=True)
    partner_id = fields.Many2one(tracking=True)
    allow_out_payment = fields.Boolean(tracking=True)
    currency_id = fields.Many2one(tracking=True)

    @api.constrains('journal_id')
    def _check_journal_id(self):
        for bank in self:
            if len(bank.journal_id) > 1:
                raise ValidationError(_('A bank account can belong to only one journal.'))

    def _build_qr_code_vals(self, amount, free_communication, structured_communication, currency, debtor_partner, qr_method=None, silent_errors=True):
        """ Returns the QR-code vals needed to generate the QR-code report link to pay this account with the given parameters,
        or None if no QR-code could be generated.

        :param amount: The amount to be paid
        :param free_communication: Free communication to add to the payment when generating one with the QR-code
        :param structured_communication: Structured communication to add to the payment when generating one with the QR-code
        :param currency: The currency in which amount is expressed
        :param debtor_partner: The partner to which this QR-code is aimed (so the one who will have to pay)
        :param qr_method: The QR generation method to be used to make the QR-code. If None, the first one giving a result will be used.
        :param silent_errors: If true, forbids errors to be raised if some tested QR-code format can't be generated because of incorrect data.
        """
        if not self:
            return None

        self.ensure_one()

        if not currency:
            raise UserError(_("Currency must always be provided in order to generate a QR-code"))

        available_qr_methods = self.get_available_qr_methods_in_sequence()
        candidate_methods = qr_method and [(qr_method, dict(available_qr_methods)[qr_method])] or available_qr_methods
        for candidate_method, candidate_name in candidate_methods:
            if self._eligible_for_qr_code(candidate_method, debtor_partner, currency):
                error_message = self._check_for_qr_code_errors(candidate_method, amount, currency, debtor_partner, free_communication, structured_communication)

                if not error_message:
                    return {
                        'qr_method': candidate_method,
                        'amount': amount,
                        'currency': currency,
                        'debtor_partner': debtor_partner,
                        'free_communication': free_communication,
                        'structured_communication': structured_communication,
                    }

                elif not silent_errors:
                    error_header = _("The following error prevented '%s' QR-code to be generated though it was detected as eligible: ", candidate_name)
                    raise UserError(error_header + error_message)

        return None

    def build_qr_code_url(self, amount, free_communication, structured_communication, currency, debtor_partner, qr_method=None, silent_errors=True):
        vals = self._build_qr_code_vals(amount, free_communication, structured_communication, currency, debtor_partner, qr_method, silent_errors)
        if vals:
            return self._get_qr_code_url(**vals)
        return None

    def build_qr_code_base64(self, amount, free_communication, structured_communication, currency, debtor_partner, qr_method=None, silent_errors=True):
        vals = self._build_qr_code_vals(amount, free_communication, structured_communication, currency, debtor_partner, qr_method, silent_errors)
        if vals:
            return self._get_qr_code_base64(**vals)
        return None

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        return None

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        raise NotImplementedError()

    def _get_qr_code_url(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        """ Hook for extension, to support the different QR generation methods.
        This function uses the provided qr_method to try generation a QR-code for
        the given data. It it succeeds, it returns the report URL to make this
        QR-code; else None.

        :param qr_method: The QR generation method to be used to make the QR-code.
        :param amount: The amount to be paid
        :param currency: The currency in which amount is expressed
        :param debtor_partner: The partner to which this QR-code is aimed (so the one who will have to pay)
        :param free_communication: Free communication to add to the payment when generating one with the QR-code
        :param structured_communication: Structured communication to add to the payment when generating one with the QR-code
        """
        params = self._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
        if params:
            params['type'] = params.pop('barcode_type')
            return '/report/barcode/?' + werkzeug.urls.url_encode(params)
        return None

    def _get_qr_code_base64(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        """ Hook for extension, to support the different QR generation methods.
        This function uses the provided qr_method to try generation a QR-code for
        the given data. It it succeeds, it returns QR code in base64 url; else None.

        :param qr_method: The QR generation method to be used to make the QR-code.
        :param amount: The amount to be paid
        :param currency: The currency in which amount is expressed
        :param debtor_partner: The partner to which this QR-code is aimed (so the one who will have to pay)
        :param free_communication: Free communication to add to the payment when generating one with the QR-code
        :param structured_communication: Structured communication to add to the payment when generating one with the QR-code
        """
        params = self._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
        if params:
            try:
                barcode = self.env['ir.actions.report'].barcode(**params)
            except (ValueError, AttributeError):
                raise werkzeug.exceptions.HTTPException(description='Cannot convert into barcode.')
            return image_data_uri(base64.b64encode(barcode))
        return None

    @api.model
    def _get_available_qr_methods(self):
        """ Returns the QR-code generation methods that are available on this db,
        in the form of a list of (code, name, sequence) elements, where
        'code' is a unique string identifier, 'name' the name to display
        to the user to designate the method, and 'sequence' is a positive integer
        indicating the order in which those mehtods need to be checked, to avoid
        shadowing between them (lower sequence means more prioritary).
        """
        return []

    @api.model
    def get_available_qr_methods_in_sequence(self):
        """ Same as _get_available_qr_methods but without returning the sequence,
        and using it directly to order the returned list.
        """
        all_available = self._get_available_qr_methods()
        all_available.sort(key=lambda x: x[2])
        return [(code, name) for (code, name, sequence) in all_available]

    def _eligible_for_qr_code(self, qr_method, debtor_partner, currency, raises_error=True):
        """ Tells whether or not the criteria to apply QR-generation
        method qr_method are met for a payment on this account, in the
        given currency, by debtor_partner. This does not impeach generation errors,
        it only checks that this type of QR-code *should be* possible to generate.
        Consistency of the required field needs then to be checked by _check_for_qr_code_errors().
        """
        return False

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        """ Checks the data before generating a QR-code for the specified qr_method
        (this method must have been checked for eligbility by _eligible_for_qr_code() first).

        Returns None if no error was found, or a string describing the first error encountered
        so that it can be reported to the user.
        """
        return None

    @api.model_create_multi
    def create(self, vals_list):
        # EXTENDS base res.partner.bank
        res = super().create(vals_list)
        for account in res:
            msg = _("Bank Account %s created", account._get_html_link(title=f"#{account.id}"))
            account.partner_id._message_log(body=msg)
        return res

    def write(self, vals):
        # EXTENDS base res.partner.bank
        # Track and log changes to partner_id, heavily inspired from account_move
        account_initial_values = defaultdict(dict)
        # Get all tracked fields (without related fields because these fields must be managed on their own model)
        tracking_fields = []
        for field_name in vals:
            field = self._fields[field_name]
            if not (hasattr(field, 'related') and field.related) and hasattr(field, 'tracking') and field.tracking:
                tracking_fields.append(field_name)
        fields_definition = self.env['res.partner.bank'].fields_get(tracking_fields)

        # Get initial values for each account
        for account in self:
            for field in tracking_fields:
                # Group initial values by partner_id
                account_initial_values[account][field] = account[field]

        res = super().write(vals)

        # Log changes to move lines on each move
        for account, initial_values in account_initial_values.items():
            tracking_value_ids = account._mail_track(fields_definition, initial_values)[1]
            if tracking_value_ids:
                msg = _("Bank Account %s updated", account._get_html_link(title=f"#{account.id}"))
                account.partner_id._message_log(body=msg, tracking_value_ids=tracking_value_ids)
                if 'partner_id' in initial_values:  # notify previous partner as well
                    initial_values['partner_id']._message_log(body=msg, tracking_value_ids=tracking_value_ids)
        return res

    def unlink(self):
        # EXTENDS base res.partner.bank
        for account in self:
            msg = _("Bank Account %s with number %s deleted", account._get_html_link(title=f"#{account.id}"), account.acc_number)
            account.partner_id._message_log(body=msg)
        return super().unlink()
