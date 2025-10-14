# -*- coding: utf-8 -*-
import base64
from collections import defaultdict

import werkzeug
import werkzeug.exceptions
from odoo import _, api, fields, models
from odoo.fields import SQL
from odoo.exceptions import UserError, ValidationError
from odoo.tools.image import image_data_uri


class ResPartnerBank(models.Model):
    _name = 'res.partner.bank'
    _inherit = ['res.partner.bank', 'mail.thread', 'mail.activity.mixin']

    journal_id = fields.One2many(
        'account.journal', 'bank_account_id', domain=[('type', '=', 'bank')], string='Account Journal', readonly=True,
        check_company=True,
        help="The accounting journal corresponding to this bank account.")
    has_iban_warning = fields.Boolean(
        compute='_compute_display_account_warning',
        help='Technical field used to display a warning if the IBAN country is different than the holder country.',
        store=True,
    )
    partner_country_name = fields.Char(related='partner_id.country_id.name')
    has_money_transfer_warning = fields.Boolean(
        compute='_compute_display_account_warning',
        help='Technical field used to display a warning if the account is a transfer service account.',
        store=True,
    )
    money_transfer_service = fields.Char(compute='_compute_money_transfer_service_name')
    partner_supplier_rank = fields.Integer(related='partner_id.supplier_rank')
    partner_customer_rank = fields.Integer(related='partner_id.customer_rank')
    related_moves = fields.One2many('account.move', inverse_name='partner_bank_id')

    # Add tracking to the base fields
    bank_id = fields.Many2one(tracking=True)
    active = fields.Boolean(tracking=True)
    acc_number = fields.Char(tracking=True)
    acc_holder_name = fields.Char(tracking=True)
    partner_id = fields.Many2one(tracking=True)
    user_has_group_validate_bank_account = fields.Boolean(compute='_compute_user_has_group_validate_bank_account')
    allow_out_payment = fields.Boolean(
        tracking=True,
        help='Sending fake invoices with a fraudulent account number is a common phishing practice. '
             'To protect yourself, always verify new bank account numbers, preferably by calling the vendor, as phishing '
             'usually happens when their emails are compromised. Once verified, you can activate the ability to send money.'
    )
    currency_id = fields.Many2one(tracking=True)
    lock_trust_fields = fields.Boolean(compute='_compute_lock_trust_fields')
    duplicate_bank_partner_ids = fields.Many2many('res.partner', compute="_compute_duplicate_bank_partner_ids")

    @api.constrains('journal_id')
    def _check_journal_id(self):
        for bank in self:
            if len(bank.journal_id) > 1:
                raise ValidationError(_('A bank account can belong to only one journal.'))

    @api.constrains('allow_out_payment')
    def _check_allow_out_payment(self):
        """ Block enabling the setting, but it can be set to false without the group. (For example, at creation) """
        for bank in self:
            if bank.allow_out_payment:
                if not self.env.user.has_group('account.group_validate_bank_account'):
                    raise ValidationError(_('You do not have the right to trust or un-trust a bank account.'))

    @api.depends('acc_number')
    def _compute_duplicate_bank_partner_ids(self):
        id2duplicates = dict(self.env.execute_query(SQL(
            """
                SELECT this.id,
                       ARRAY_AGG(other.partner_id)
                  FROM res_partner_bank this
             LEFT JOIN res_partner_bank other ON this.acc_number = other.acc_number
                                             AND this.id != other.id
                                             AND other.active = TRUE
                 WHERE this.id = ANY(%(ids)s)
                 AND other.partner_id IS NOT NULL
                   AND this.active = TRUE
                   AND (
                        ((this.company_id = other.company_id) OR (this.company_id IS NULL AND other.company_id IS NULL))
                        OR
                        other.company_id IS NULL
                        )
              GROUP BY this.id
            """,
            ids=self.ids,
        )))
        for bank in self:
            bank.duplicate_bank_partner_ids = self.env['res.partner'].browse(id2duplicates.get(bank._origin.id))

    @api.depends('partner_id.country_id', 'sanitized_acc_number', 'allow_out_payment', 'acc_type')
    def _compute_display_account_warning(self):
        for bank in self:
            if bank.allow_out_payment or not bank.sanitized_acc_number or bank.acc_type != 'iban':
                bank.has_iban_warning = False
                bank.has_money_transfer_warning = False
                continue
            bank_country = bank.sanitized_acc_number[:2]
            bank.has_iban_warning = bank.partner_id.country_id and bank_country != bank.partner_id.country_id.code

            bank_institution_code = bank.sanitized_acc_number[4:7]
            bank.has_money_transfer_warning = bank_institution_code in bank._get_money_transfer_services()

    @api.depends('sanitized_acc_number', 'allow_out_payment')
    def _compute_money_transfer_service_name(self):
        for bank in self:
            if bank.sanitized_acc_number:
                bank_institution_code = bank.sanitized_acc_number[4:7]
                bank.money_transfer_service = bank._get_money_transfer_services().get(bank_institution_code, False)
            else:
                bank.money_transfer_service = False

    def _get_money_transfer_services(self):
        return {
            '967': 'Wise',
            '977': 'Paynovate',
            '974': 'PPS EU SA',
        }

    @api.depends('acc_number')
    @api.depends_context('uid')
    def _compute_user_has_group_validate_bank_account(self):
        user_has_group_validate_bank_account = self.env.user.has_group('account.group_validate_bank_account')
        for bank in self:
            bank.user_has_group_validate_bank_account = user_has_group_validate_bank_account

    @api.depends('allow_out_payment')
    def _compute_lock_trust_fields(self):
        for bank in self:
            if not bank._origin or not bank.allow_out_payment:
                bank.lock_trust_fields = False
            elif bank._origin and bank.allow_out_payment:
                bank.lock_trust_fields = True

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
            error_message = self._get_error_messages_for_qr(candidate_method, debtor_partner, currency)
            if not error_message:
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

            if not silent_errors:
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
        return '/report/barcode/?' + werkzeug.urls.url_encode(params) if params else None

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

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        """ Tells whether or not the criteria to apply QR-generation
        method qr_method are met for a payment on this account, in the
        given currency, by debtor_partner. This does not impeach generation errors,
        it only checks that this type of QR-code *should be* possible to generate.
        If not, returns an adequate error message to be displayed to the user if need be.
        Consistency of the required field needs then to be checked by _check_for_qr_code_errors().
        :returns:  None if the qr method is eligible, or the error message
        """
        return None

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        """ Checks the data before generating a QR-code for the specified qr_method
        (this method must have been checked for eligbility by _get_error_messages_for_qr() first).

        Returns None if no error was found, or a string describing the first error encountered
        so that it can be reported to the user.
        """
        return None

    @api.model_create_multi
    def create(self, vals_list):
        # EXTENDS base res.partner.bank

        if not self.env.user.has_group('account.group_validate_bank_account'):
            for vals in vals_list:
                # force the allow_out_payment field to False in order to prevent scam payments on newly created bank accounts
                vals['allow_out_payment'] = False

        for vals in vals_list:
            if (partner_id := vals.get('partner_id')) and (acc_number := vals.get('acc_number')):
                archived_res_partner_bank = self.env['res.partner.bank'].search([('active', '=', False), ('partner_id', '=', partner_id), ('acc_number', '=', acc_number)])
                if archived_res_partner_bank:
                    raise UserError(_("A bank account with Account Number %(number)s already exists for Partner %(partner)s, but is archived. Please unarchive it instead.", number=acc_number, partner=archived_res_partner_bank.partner_id.name))

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

        # Some fields should not be editable based on conditions. It is enforced in the view, but not in python which
        # leaves them vulnerable to edits via the shell/... So we need to ensure that the user has the rights to edit
        # these fields when writing too.
        # While we do lock changes if the account is trusted, we still want to allow to change them if we go from not trusted -> trusted or from trusted -> not trusted.
        trusted_accounts = self.filtered(lambda x: x.lock_trust_fields)
        if not trusted_accounts:
            should_allow_changes = True  # If we were on a non-trusted account, we will allow to change (setting/... one last time before trusting)
        else:
            # If we were on a trusted account, we only allow changes if the account is moving to untrusted.
            should_allow_changes = ('allow_out_payment' in vals and vals['allow_out_payment'] is False)

        lock_fields = {'acc_number', 'sanitized_acc_number', 'partner_id', 'acc_type'}
        if not should_allow_changes and any(
            account[fname] != account._fields[fname].convert_to_record(
                account._fields[fname].convert_to_cache(vals[fname], account),
                account,
            )
            for fname in lock_fields & set(vals)
            for account in trusted_accounts
        ):
            raise UserError(_("You cannot modify the account number or partner of an account that has been trusted."))

        if 'allow_out_payment' in vals and not self.env.user.has_group('account.group_validate_bank_account') and not self.env.su:
            raise UserError(_("You do not have the rights to trust or un-trust accounts."))

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
            msg = _("Bank Account %(link)s with number %(number)s archived", link=account._get_html_link(title=f"#{account.id}"), number=account.acc_number)
            account.partner_id._message_log(body=msg)
        return super().unlink()

    def default_get(self, fields_list):
        if 'acc_number' not in fields_list:
            return super().default_get(fields_list)

        # When create & edit, `name` could be used to pass (in the context) the
        # value input by the user. However, we want to set the default value of
        # `acc_number` variable instead.
        default_acc_number = self._context.get('default_acc_number', False) or self._context.get('default_name', False)
        return super(ResPartnerBank, self.with_context(default_acc_number=default_acc_number)).default_get(fields_list)

    @api.depends('allow_out_payment', 'acc_number', 'bank_id')
    @api.depends_context('display_account_trust')
    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get('display_account_trust'):
            for acc in self:
                trusted_label = _('trusted') if acc.allow_out_payment else _('untrusted')
                if acc.bank_id:
                    name = f'{acc.acc_number} - {acc.bank_id.name} ({trusted_label})'
                else:
                    name = f'{acc.acc_number} ({trusted_label})'
                acc.display_name = name
