from odoo import api, fields, models, modules
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.addons.iap.tools import iap_tools

ENDPOINT = 'https://pdp.odoo.com'
TEST_ENDPOINT = 'https://pdp.test.odoo.com'


class PdpRegistration(models.TransientModel):
    _name = 'pdp.registration'
    _description = "PDP Registration"

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    contact_email = fields.Char(
        related='company_id.account_peppol_contact_email',
        readonly=False,
        required=True,
    )
    pdp_identifier = fields.Char(
        related='company_id.pdp_identifier',
        readonly=False,
        required=True,
    )
    pdp_pilot_phase = fields.Boolean(
        related='company_id.l10n_fr_pdp_pilot_phase',
        readonly=False,
        string=" Pilot Phase",
        help="Participate in the Pilot Phase of the French E-Invoicing. This way you are able to test it before it becomes mandatory.",
    )
    edi_mode = fields.Selection(
        string='EDI mode',
        selection=[('demo', 'Demo'), ('test', 'Test'), ('prod', 'Live')],
        compute='_compute_edi_mode',
        readonly=False,
    )
    edi_user_id = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        string='EDI user',
        compute='_compute_edi_user_id',
    )
    account_peppol_proxy_state = fields.Selection(
        related='company_id.account_peppol_proxy_state',
        readonly=False,
    )
    warnings = fields.Json(
        string="Warnings",
        compute="_compute_warnings",
    )
    siren_number = fields.Char(
        compute='_compute_siren_number',
        store=True,
        readonly=False
    )
    pdp_authentication_uuid = fields.Char(
        string="Authentication IAP UUID",
    )
    pdp_kyc_status = fields.Selection(
        string="Authentication status",
        related='company_id.pdp_kyc_status',
        readonly=False,
    )
    auth_url_hash = fields.Char(
        string="Company Authentication IAP UUID",
        related="company_id.pdp_authentication_uuid",
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('pdp_identifier')
    def _onchange_pdp_identifier(self):
        for wizard in self:
            if wizard.pdp_identifier:
                wizard.pdp_identifier = ''.join(char for char in wizard.pdp_identifier if char == '_' or char.isalnum())

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id.company_registry')
    def _compute_siren_number(self):
        for wizard in self:
            wizard.siren_number = wizard.company_id.company_registry[:9] if wizard.company_id.company_registry else ''

    @api.depends('company_id.account_edi_proxy_client_ids')
    def _compute_edi_user_id(self):
        for wizard in self:
            wizard.edi_user_id = wizard.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'pdp')[:1]

    @api.depends('edi_user_id')
    def _compute_edi_mode(self):
        for wizard in self:
            wizard.edi_mode = wizard.company_id._get_peppol_edi_mode()

    @api.depends('pdp_identifier')
    def _compute_warnings(self):
        for wizard in self:
            warnings = {}
            # Check identifier
            if (
                wizard.pdp_identifier
                and not self.env["res.company"]._check_pdp_identifier(wizard.pdp_identifier, warning=True)
            ):
                warnings['company_pdp_identifier_warning'] = {
                    'level': 'warning',
                    'message': self.env._("The endpoint number might not be correct. "
                                          "Please check if you entered the right identification number."),
                }
            # Check whether the identifier is already associated with a platform on the annuaire
            if (
                wizard.pdp_identifier
                and (participant_info := wizard.company_id.partner_id._pdp_annuaire_lookup_participant(f"0225:{wizard.pdp_identifier}")) is not None
                and participant_info.get('platform_id')
                and not participant_info.get('receiver_on_odoo')
               ):
                platform_name = participant_info.get("platform_name")
                warnings["company_pdp_annuaire_warning"] = {
                    "level": "warning",
                    "message": self.env._(
                        "Another platform is already assigned to this identifier in the annuaire (Platform%(platform_name)s with ID %(platform_id)s). "
                        "If you previously registered with an Approved Platform, please unregister.",
                        platform_name=f" '{platform_name}'" if platform_name else "",
                        platform_id=participant_info.get("platform_id"),
                    ),
                }
            wizard.warnings = warnings or False

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _ensure_mandatory_fields(self):
        if not self.contact_email:
            raise ValidationError(self.env._("The contact email is required."))

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

    def _action_open_pdp_form(self, reopen=True):
        if not self.env.user.totp_enabled and not bool(self.env['ir.config_parameter'].sudo().get_param('auth_totp.policy')):
            raise RedirectWarning(
                message=self.env._("To be able to register, you need to enable the two-factor authentication."),
                action=self.env.user._get_records_action(
                    target='new',
                    views=[(self.env.ref('base.view_users_form_simple_modif').id, "form")],
                ),
                button_text=self.env._("Go to the Preferences panel"),
            )
        return self._get_records_action(
            name=self.env._("Send via French electronic invoicing"),
            target='new',
        )

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def button_trigger_authentication(self):
        self.ensure_one()
        if not self.siren_number:
            raise RedirectWarning(
                message=self.env._("You need to have a valid siren number to authenticate."),
                action=self.company_id._get_records_action(),
                button_text=self.env._("Go to company"),
            )
        base_url = ENDPOINT if self.edi_mode == 'prod' else TEST_ENDPOINT
        response = iap_tools.iap_jsonrpc(f'{base_url}/api/id_authentication/1/authentication', params={
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'vat': self.siren_number,
            'auth_email': self.contact_email,
            'company_name': self.company_id.name,
            'localization': 'FR',
        })
        self.pdp_authentication_uuid = response.get('object_uuid')
        self.auth_url_hash = response.get('url_hash')
        self.pdp_kyc_status = 'processing'

        return {
            'type': 'ir.actions.act_url',
            'url': f'{base_url}/api/id_authentication/1/authentication_portal/{self.auth_url_hash}',
            'target': 'new',
        }

    def _display_status_notification(self):
        self.ensure_one()
        if self.pdp_kyc_status == 'success':
            type_color = 'success'
            message = self.env._("Identity verified.")
            next_action = self._action_open_pdp_form()
        elif self.pdp_kyc_status == 'fail':
            type_color = 'danger'
            message = self.env._("Authentication failed.")
            next_action = {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': type_color,
                'sticky': True,
                'next': next_action,
            },
        }

    def button_refresh_authentication(self):
        self.ensure_one()
        base_url = ENDPOINT if self.edi_mode == 'prod' else TEST_ENDPOINT
        response = iap_tools.iap_jsonrpc(f'{base_url}/api/signaturit_id_authentication/1/kyc_status', params={
            'object_uuid': self.pdp_authentication_uuid,
        })
        kyc_status = response.get('kyc_status')
        if kyc_status in ('success', 'fail'):
            self.pdp_kyc_status = kyc_status
            return self._display_status_notification()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': self.env._("Status updated."),
                'type': 'success',
                'next': self._action_open_pdp_form(),
            },
        }

    def button_open_authentication_link(self):
        self.ensure_one()
        base_url = ENDPOINT if self.edi_mode == 'prod' else TEST_ENDPOINT
        return {
            'type': 'ir.actions.act_url',
            'url': f'{base_url}/api/id_authentication/1/authentication_portal/{self.auth_url_hash}',
            'target': 'new',
        }

    def button_cancel_authentication(self):
        self.ensure_one()
        self.pdp_kyc_status = 'fail'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': self.env._("Authentication cancelled"),
                'type': 'danger',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def button_register_pdp_participant(self):
        self.ensure_one()

        self._ensure_mandatory_fields()

        if self.account_peppol_proxy_state in ('smp_registration', 'receiver'):
            pdp_state_translated = dict(self._fields['account_peppol_proxy_state']._description_selection(self.env))[self.account_peppol_proxy_state]
            raise UserError(self.env._("Cannot register a user with a '%s' application", pdp_state_translated))

        if self.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol'):
            raise UserError(self.env._("There is a connection to Peppol (non-PA) already"))

        if not self.env["res.company"]._check_pdp_identifier(self.pdp_identifier):
            raise UserError(self.env._("The Identifier is not valid. The expected format is: SIREN, SIREN_SIRET, SIREN_SIRET_CodeRoutage or SIREN_SuffixeAdressage"))

        edi_user = self.edi_user_id or self.env['account_edi_proxy_client.user']._register_proxy_user(self.company_id, 'pdp', self.edi_mode)

        # if there is an error when activating the participant below,
        # the client side is rolled back and the edi user is deleted on the client side
        # but remains on the proxy side.
        # it is important to keep these two in sync, so commit before activating.
        if not modules.module.current_test:
            self.env.cr.commit()

        if self.account_peppol_proxy_state not in ('smp_registration', 'receiver'):
            edi_user._pdp_register_receiver()
            self.invalidate_recordset()  # registering may i.e. have changed self.account_peppol_proxy_state

        notifications = {
            False: self.env._('Something went wrong.'),
            'smp_registration': self.env._('Your registration will be activated soon.'),
            'receiver': self.env._('You can now send and receive electronic invoices.'),
            'rejected': self.env._('Your registration has been rejected.'),
        }
        return self._action_send_notification(
            title="PA Status",
            message=notifications[self.account_peppol_proxy_state],
        )

    def button_deregister_pdp_participant(self):
        """
        Deregister the edi user from PDP network
        """
        self.ensure_one()

        if self.edi_user_id:
            self.edi_user_id._peppol_deregister_participant()
