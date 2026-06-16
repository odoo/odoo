import logging

from odoo import api, fields, models, modules
from odoo.exceptions import UserError, ValidationError, RedirectWarning

from odoo.addons.l10n_fr_pdp.tools.demo_utils import handle_demo
from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)


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
        compute="_compute_pdp_identifier",
        inverse="_inverse_pdp_identifier",
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
        readonly=False,
    )
    pdp_authentication_uuid = fields.Char(
        string="Authentication IAP UUID",
        related="company_id.pdp_authentication_uuid",
        store=True,  # Keeping it stored as it's a stored field in stable.
        readonly=False,
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

    @api.depends('company_id.pdp_identifier')
    def _compute_pdp_identifier(self):
        for wizard in self:
            wizard.pdp_identifier = wizard.company_id.pdp_identifier or wizard.company_id.partner_id._get_suggested_pdp_identifier()

    def _inverse_pdp_identifier(self):
        for record in self:
            record.company_id.pdp_identifier = record.pdp_identifier

    @api.depends('company_id.siret', 'company_id.company_registry')
    def _compute_siren_number(self):
        for wizard in self:
            wizard.siren_number = wizard.company_id.partner_id._l10n_fr_pdp_get_siren()

    @api.depends('company_id.account_edi_proxy_client_ids')
    def _compute_edi_user_id(self):
        for wizard in self:
            wizard.edi_user_id = wizard.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'pdp')[:1]

    @api.depends('edi_user_id')
    def _compute_edi_mode(self):
        for wizard in self:
            wizard.edi_mode = wizard.company_id._get_peppol_edi_mode()

    @api.depends('pdp_identifier', 'siren_number')
    def _compute_warnings(self):
        for wizard in self:
            warnings = {}
            # Check SIREN
            if not wizard.siren_number:
                warnings['company_siren_warning'] = {
                    'level': 'warning',
                    'message': self.env._("The SIREN of the company could not be determined."),
                    'action_text': self.env._("Go to company"),
                    'action': wizard.company_id._get_records_action(name=self.env._("Check Company Data")),
                }
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

    def _check_can_register(self):
        """ No longer used, need to remove in master """
        if not self.env.user.totp_enabled and not bool(self.env['ir.config_parameter'].sudo().get_param('auth_totp.policy')) and self.edi_mode != 'demo':
            raise RedirectWarning(
                message=self.env._("To be able to register, you need to enable the two-factor authentication."),
                action=self.env.user._get_records_action(
                    target='new',
                    views=[(self.env.ref('base.view_users_form_simple_modif').id, "form")],
                ),
                button_text=self.env._("Go to the Preferences panel"),
            )

    def _action_open_pdp_form(self, reopen=True):
        self.ensure_one()
        return self._get_records_action(
            name=self.env._("Send via French electronic invoicing"),
            target='new',
        )

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @handle_demo
    def button_trigger_authentication(self):
        self.ensure_one()
        if not self.siren_number:
            raise RedirectWarning(
                message=self.env._("You need to have a valid siren number to authenticate."),
                action=self.company_id._get_records_action(),
                button_text=self.env._("Go to company"),
            )
        base_url = self.company_id._pdp_get_iap_url()
        response = iap_tools.iap_jsonrpc(f'{base_url}/api/id_authentication/1/authentication', params={
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'vat': self.siren_number,
            'auth_email': self.contact_email,
            'company_name': self.company_id.name,
            'localization': 'FR',
            'db_url': self.get_base_url(),
        })
        if error := response.get('error'):
            raise UserError(error)

        self.pdp_authentication_uuid = response.get('object_uuid')

        if not self.pdp_authentication_uuid or not response.get('url_hash'):
            raise UserError(self.env._("Something wrong happened."))
        self.pdp_kyc_status = 'processing'

        return {
            'type': 'ir.actions.act_url',
            'url': f'{base_url}/api/id_authentication/1/authentication_portal/{response["url_hash"]}',
            'target': 'new',
        }

    def _get_status_notification_data(self):
        self.ensure_one()
        if self.pdp_kyc_status == 'success':
            return {
                'message': self.env._("Identity verified."),
                'type': 'success',
                'sticky': True,
                'next': self._action_open_pdp_form(),
            }
        elif self.pdp_kyc_status == 'fail':
            return {
                'message': self.env._("Authentication failed."),
                'type': 'danger',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        return {
            'message': self.env._("Status updated."),
            'type': 'info',
            'sticky': False,
            'next': self._action_open_pdp_form(),
        }

    def _display_status_notification(self):
        self.ensure_one()
        data = self._get_status_notification_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': data['message'],
                'type': data['type'],
                'sticky': data['sticky'],
                'next': data['next'],
            },
        }

    def display_status_notification_from_uuid(self):
        self.ensure_one()
        return self._display_status_notification()

    def button_refresh_authentication(self):
        self.ensure_one()
        self.company_id._refresh_pdp_authentication_status()
        return self._display_status_notification()

    def button_open_authentication_link(self):
        self.ensure_one()
        base_url = self.company_id._pdp_get_iap_url()
        response = iap_tools.iap_jsonrpc(f'{base_url}/api/id_authentication/1/get_authentication_hash', params={
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'vat': self.siren_number,
            'auth_email': self.contact_email,
            'object_uuid': self.pdp_authentication_uuid,
        })
        if error := response.get('error'):
            raise UserError(error)

        if not response.get('url_hash'):
            raise UserError(self.env._("Something wrong happened."))

        return {
            'type': 'ir.actions.act_url',
            'url': f'{base_url}/api/id_authentication/1/authentication_portal/{response["url_hash"]}',
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

        self.company_id.pdp_identifier = self.pdp_identifier  # For the initial compute the inverse is not triggered.
        edi_user = self.edi_user_id or self.env['account_edi_proxy_client.user']._register_proxy_user(self.company_id, 'pdp', self.edi_mode)

        # if there is an error when activating the participant below,
        # the client side is rolled back and the edi user is deleted on the client side
        # but remains on the proxy side.
        # it is important to keep these two in sync, so commit before activating.
        if not modules.module.current_test:
            self.env.cr.commit()

        if self.account_peppol_proxy_state not in ('smp_registration', 'receiver'):
            edi_user._peppol_register_receiver()
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
