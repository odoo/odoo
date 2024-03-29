import contextlib
try:
    import phonenumbers
except ImportError:
    phonenumbers = None

from odoo import api, fields, models, modules, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.l10n_dk_nemhandel.tools.demo_utils import handle_demo


class NemhandelRegistration(models.TransientModel):
    _name = 'nemhandel.registration'
    _description = "Nemhandel Registration"

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    contact_email = fields.Char(
        related='company_id.nemhandel_contact_email', readonly=False,
        required=True,
    )
    edi_mode = fields.Selection(
        string='EDI mode',
        selection=[('demo', 'Demo'), ('test', 'Test'), ('prod', 'Live')],
        compute='_compute_edi_mode',
        inverse='_inverse_edi_mode',
        readonly=False,
    )
    edi_user_id = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        string='EDI user',
        compute='_compute_edi_user_id',
    )
    edi_mode_constraint = fields.Selection(
        selection=[('demo', 'Demo'), ('test', 'Test'), ('prod', 'Live')],
        compute='_compute_edi_mode_constraint',
        help="Using the config params, this field specifies which edi modes may be selected from the UI"
    )
    phone_number = fields.Char(related='company_id.nemhandel_phone_number', readonly=False, inverse='_inverse_phone_number')
    l10n_dk_nemhandel_proxy_state = fields.Selection(related='company_id.l10n_dk_nemhandel_proxy_state', readonly=False)
    verification_code = fields.Char(related='edi_user_id.nemhandel_verification_code', readonly=False)
    identifier_type = fields.Selection(related='company_id.nemhandel_identifier_type', readonly=False, required=True)
    identifier_value = fields.Char(related='company_id.nemhandel_identifier_value', readonly=False, required=True)

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('identifier_value')
    def _onchange_identifier_value(self):
        for wizard in self:
            if wizard.identifier_value:
                wizard.identifier_value = ''.join(char for char in wizard.identifier_value if char.isalnum())

    @api.onchange('phone_number')
    def _onchange_phone_number(self):
        if self.phone_number:
            self.company_id._sanitize_nemhandel_phone_number(self.phone_number)
            with contextlib.suppress(phonenumbers.NumberParseException):
                parsed_phone_number = phonenumbers.parse(
                    self.phone_number,
                    region=self.company_id.country_code,
                )
                self.phone_number = phonenumbers.format_number(
                    parsed_phone_number,
                    phonenumbers.PhoneNumberFormat.E164,
                )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id.account_edi_proxy_client_ids')
    def _compute_edi_user_id(self):
        for wizard in self:
            wizard.edi_user_id = wizard.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'nemhandel')[:1]

    @api.depends('edi_user_id')
    def _compute_edi_mode_constraint(self):
        mode_constraint = self.env['ir.config_parameter'].sudo().get_param('l10n_dk_nemhandel.mode_constraint')
        trial_param = self.env['ir.config_parameter'].sudo().get_param('saas_trial.confirm_token')
        self.edi_mode_constraint = trial_param and 'demo' or mode_constraint or 'prod'

    @api.depends('edi_user_id')
    def _compute_edi_mode(self):
        edi_mode = self.env['ir.config_parameter'].sudo().get_param('l10n_dk_nemhandel.edi.mode')
        for wizard in self:
            if wizard.edi_user_id:
                wizard.edi_mode = wizard.edi_user_id.edi_mode
            else:
                wizard.edi_mode = edi_mode or 'prod'

    def _inverse_edi_mode(self):
        for wizard in self:
            if not wizard.edi_user_id and wizard.edi_mode:
                self.env['ir.config_parameter'].sudo().set_param('l10n_dk_nemhandel.edi.mode', wizard.edi_mode)

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _action_open_nemhandel_form(self, reopen=True):
        if reopen:
            return self._get_records_action(
                name=_("Send via Nemhandel"),
                res_id=self.id,
                target='new',
                context={**self.env.context, 'disable_sms_verification': True}
            )

        return self._get_records_action(
            name=_("Send via Nemhandel"),
            target='new'
        )

    def _action_send_notification(self, title, message):
        move_ids = self.env.context.get('active_ids')
        if move_ids and self.env.context.get('active_model') == 'account.move':
            next_action = self.env['account.move'].browse(move_ids).action_send_and_print()
            next_action['views'] = [(False, 'form')]
        else:
            next_action = {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'type': 'success',
                'message': message,
                'next': next_action,
            }
        }

    @handle_demo
    def button_nemhandel_registration_sms(self):
        """
        The first step of the Nemhandel onboarding.
        - Creates an EDI proxy user on the iap side, then the client side
        - Calls /activate_participant to mark the EDI user as nemhandel user
        - Sends a SMS code
        """
        self.ensure_one()

        if self.l10n_dk_nemhandel_proxy_state != 'not_registered':
            raise UserError(_('Cannot register a user with a %s application', self.l10n_dk_nemhandel_proxy_state))

        if not self.phone_number:
            raise ValidationError(_("Please enter a phone number to verify your application."))
        if not self.contact_email:
            raise ValidationError(_("Please enter a primary contact email to verify your application."))
        if not self.env.company.vat:
            raise RedirectWarning(
                _("Please fill in your company's VAT"),
                self.env.ref('base.action_res_company_form'),
                _('Company settings')
            )

        company = self.company_id
        self.edi_user_id._check_company_on_nemhandel(self.company_id, f'{self.identifier_type}:{self.identifier_value}')

        if not self.edi_user_id:
            edi_user = self.edi_user_id.sudo()._register_proxy_user(company, 'nemhandel', self.edi_mode)
            self.edi_user_id = edi_user

            # if there is an error when activating the participant below,
            # the client side is rolled back and the edi user is deleted on the client side
            # but remains on the proxy side.
            # it is important to keep these two in sync, so commit before activating.
            if not modules.module.current_test:
                self.env.cr.commit()

        vat = company.vat[2:] if company.vat[:2].isalpha() else company.vat
        params = {
            'company_details': {
                'nemhandel_phone_number': self.phone_number,
                'nemhandel_contact_email': self.contact_email,
                'nemhandel_company_cvr': vat,
                'nemhandel_company_name': company.name,
                'nemhandel_country_code': company.country_id.code,
            },
        }

        self.edi_user_id._call_nemhandel_proxy(
            endpoint='/api/nemhandel/1/activate_participant',
            params=params,
        )

        if self.edi_user_id.edi_mode != 'demo':
            return self.send_nemhandel_verification_code()
        return self._action_open_nemhandel_form()

    @handle_demo
    def button_nemhandel_receiver_registration(self):
        """
        The user is registered on the Nemhandel network, i.e. can receive documents from other Nemhandel participants.
        """
        self.ensure_one()
        try:
            self.edi_user_id._nemhandel_register_as_receiver()
        except (UserError, AccountEdiProxyError) as e:
            self.button_deregister_nemhandel_participant()
            registration_form_action = self._action_open_nemhandel_form()
            registration_form_action['views'] = [(False, 'form')]
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': e,
                    'next': registration_form_action,
                }
            }

        if self.company_id.l10n_dk_nemhandel_proxy_state == 'receiver':
            return self._action_send_notification(
                title=_("Registered to receive documents."),
                message=_("You can now receive documents via Nemhandel."),
            )
        return self._action_open_nemhandel_form()

    @handle_demo
    def button_update_nemhandel_user_data(self):
        """
        Action for the user to be able to update their contact details any time
        Calls /update_user on the iap server
        """
        self.ensure_one()

        if not self.contact_email or not self.phone_number:
            raise ValidationError(_("Contact email and phone number are required."))

        edi_identification = f'{self.identifier_type}/{self.identifier_value}'
        self.edi_user_id._check_company_on_nemhandel(self.company_id, edi_identification)

        params = {
            'update_data': {
                'edi_identification': edi_identification,
                'nemhandel_phone_number': self.phone_number,
                'nemhandel_contact_email': self.contact_email,
            }
        }

        self.edi_user_id._call_nemhandel_proxy(
            endpoint='/api/nemhandel/1/update_user',
            params=params,
        )

    def send_nemhandel_verification_code(self, resend=False):
        """
        Request user verification via SMS
        Calls the /send_verification_code to send the 6-digit verification code
        """
        self.ensure_one()

        if resend:
            self.button_update_nemhandel_user_data()
        self.edi_user_id._call_nemhandel_proxy(
            endpoint='/api/nemhandel/1/send_verification_code',
            params={'message': _("Your confirmation code is")},
        )
        self.l10n_dk_nemhandel_proxy_state = 'in_verification'
        return self._action_open_nemhandel_form()

    @handle_demo
    def button_check_nemhandel_verification_code(self):
        """
        Calls /verify_phone_number to compare user's input and the
        code generated on the IAP server
        """
        self.ensure_one()
        if self.l10n_dk_nemhandel_proxy_state != 'in_verification':
            raise ValidationError(_("Please first verify your phone number by clicking on 'Send a registration code by SMS'."))

        if not self.verification_code or len(self.verification_code) != 6:
            raise ValidationError(_("The verification code should contain six digits."))

        # update contact details in case the user made changes
        self.button_update_nemhandel_user_data()

        self.edi_user_id._call_nemhandel_proxy(
            endpoint='/api/nemhandel/1/verify_phone_number',
            params={'verification_code': self.verification_code},
        )
        self.verification_code = False

        return self.button_nemhandel_receiver_registration()

    @handle_demo
    def button_deregister_nemhandel_participant(self):
        """
        Deregister the edi user from Nemhandel network
        """
        self.ensure_one()

        if self.edi_user_id:
            self.edi_user_id._nemhandel_deregister_participant()
        return True
