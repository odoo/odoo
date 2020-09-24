# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from datetime import datetime


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def write(self, vals):
        # bank account of partner changed, warn self.env.user
        for acc in self:
            if 'acc_number' in vals:
                mail_template = self.env.ref('account.partner_bank_account_changed_template')
                ctx = {
                    'user_name': self.env.user.name,
                    'partner': acc.partner_id,
                    'timestamp': fields.Datetime.context_timestamp(self, datetime.now()).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'operations': [_('an account was edited')]
                }
                kwargs = {
                    'subject': _('Warning: bank account of %s modified', acc.partner_id.name),
                    'partner_ids': self.env.user.partner_id.ids,
                    'body': mail_template._render(ctx, engine='ir.qweb', minimal_qcontext=True),
                    'notify_by_email': True,
                }
                self.env['mail.thread'].with_context(mail_notify_author=True).message_notify(**kwargs)

                acc.partner_id.message_post(body=_('<ul><li>Bank account number: %s <div class="fa fa-long-arrow-right"/> %s</ul></li>', acc.acc_number, vals['acc_number']))
        return super().write(vals)

    def build_qr_code_url(self, amount, free_communication, structured_communication, currency, debtor_partner, qr_method=None, silent_errors=True):
        """ Returns the QR-code report URL to pay to this account with the given parameters,
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
                    return self._get_qr_code_url(candidate_method, amount, currency, debtor_partner, free_communication, structured_communication)

                elif not silent_errors:
                    error_header = _("The following error prevented '%s' QR-code to be generated though it was detected as eligible: ", candidate_name)
                    raise UserError( error_header + error_message)

        return None

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


    def _eligible_for_qr_code(self, qr_method, debtor_partner, currency):
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