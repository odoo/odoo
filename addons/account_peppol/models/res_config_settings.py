# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError, ValidationError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.account_peppol.tools.demo_utils import handle_demo


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_peppol_edi_user = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        string='EDI user',
        compute='_compute_account_peppol_edi_user',
    )
    account_peppol_contact_email = fields.Char(related='company_id.account_peppol_contact_email', readonly=False)
    account_peppol_eas = fields.Selection(related='company_id.peppol_eas', readonly=False)
    account_peppol_edi_identification = fields.Char(related='account_peppol_edi_user.edi_identification')
    account_peppol_endpoint = fields.Char(related='company_id.peppol_endpoint', readonly=False)
    account_peppol_endpoint_warning = fields.Char(
        string="Warning",
        compute="_compute_account_peppol_endpoint_warning",
    )
    account_peppol_phone_number = fields.Char(related='company_id.account_peppol_phone_number', readonly=False)
    account_peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state', readonly=False)
    account_peppol_purchase_journal_id = fields.Many2one(related='company_id.peppol_purchase_journal_id', readonly=False)
    is_account_peppol_participant = fields.Boolean(
        string='Use PEPPOL',
        related='company_id.is_account_peppol_participant', readonly=False,
        help='Register as a PEPPOL user',
    )
    account_peppol_edi_mode = fields.Selection(
        selection=[('demo', 'Demo'), ('test', 'Test'), ('prod', 'Live')],
        compute='_compute_account_peppol_edi_mode',
        inverse='_inverse_account_peppol_edi_mode',
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _call_peppol_proxy(self, endpoint, params=None, edi_user=None):
        errors = {
            'code_incorrect': _('The verification code is not correct'),
            'code_expired': _('This verification code has expired. Please request a new one.'),
            'too_many_attempts': _('Too many attempts to request an SMS code. Please try again later.'),
        }

        if not edi_user:
            edi_user = self.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.edi_format_id.code == 'peppol')
        peppol_edi_format = self.env.ref('account_peppol.edi_peppol', raise_if_not_found=False)
        if not peppol_edi_format:
            raise UserError(_("Missing record 'account_peppol.edi_peppol' (Peppol Account EDI Format)"))

        params = params or {}
        try:
            response = edi_user._make_request(
                f"{edi_user._get_server_url_new(edi_format=peppol_edi_format)}{endpoint}",
                params=params,
            )
        except AccountEdiProxyError as e:
            raise UserError(e.message)

        if 'error' in response:
            error_code = response['error'].get('code')
            error_message = response['error'].get('message') or response['error'].get('data', {}).get('message')
            raise UserError(errors.get(error_code) or error_message or _('Connection error, please try again later.'))
        return response

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('account_peppol_endpoint')
    def _onchange_account_peppol_endpoint(self):
        if self.account_peppol_endpoint:
            self.account_peppol_endpoint = ''.join(char for char in self.account_peppol_endpoint if char.isalnum())

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('is_account_peppol_eligible', 'account_peppol_edi_user')
    def _compute_account_peppol_edi_mode(self):
        for config in self:
            config.account_peppol_edi_mode = config.company_id._get_peppol_edi_mode()

    def _inverse_account_peppol_edi_mode(self):
        for config in self:
            if not config.account_peppol_edi_user and config.account_peppol_edi_mode:
                self.env['ir.config_parameter'].sudo().set_param('account_edi_proxy_client.demo', config.account_peppol_edi_mode)
                return

    @api.depends("company_id.account_edi_proxy_client_ids")
    def _compute_account_peppol_edi_user(self):
        for config in self:
            config.account_peppol_edi_user = config.company_id.account_edi_proxy_client_ids.filtered(
                lambda u: u.edi_format_id.code == 'peppol')

    @api.depends('account_peppol_eas', 'account_peppol_endpoint')
    def _compute_account_peppol_endpoint_warning(self):
        for config in self:
            if (
                not config.account_peppol_eas
                or config.company_id._check_peppol_endpoint_number(warning=True)
            ):
                config.account_peppol_endpoint_warning = False
            else:
                config.account_peppol_endpoint_warning = _("The endpoint number might not be correct. "
                                                           "Please check if you entered the right identification number.")

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @handle_demo
    def button_create_peppol_proxy_user(self):
        """
        The first step of the Peppol onboarding.
        - Creates an EDI proxy user on the iap side, then the client side
        - Calls /activate_participant to mark the EDI user as peppol user
        """
        self.ensure_one()

        if self.account_peppol_proxy_state != 'not_registered':
            raise UserError(
                _('Cannot register a user with a %s application', self.account_peppol_proxy_state))

        if not self.account_peppol_phone_number:
            raise ValidationError(_("Please enter a mobile number to verify your application."))
        if not self.account_peppol_contact_email:
            raise ValidationError(_("Please enter a primary contact email to verify your application."))

        company = self.company_id
        peppol_edi_format = self.env.ref('account_peppol.edi_peppol', raise_if_not_found=False)
        if not peppol_edi_format:
            raise UserError(_("Missing record 'account_peppol.edi_peppol' (Peppol Account EDI Format)"))
        edi_identification = peppol_edi_format._get_proxy_identification(company)

        recovered_edi_users = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(company, peppol_identifier=edi_identification)
        if recovered_edi_users:
            return

        company.partner_id._check_peppol_eas()
        participant_info = company.partner_id._check_peppol_participant_exists(edi_identification, check_company=True)

        if participant_info:
            error_msg = _(
                "A participant with these details has already been registered on the network. "
                "If you have previously registered to a Peppol service, please deregister."
            )

            if isinstance(participant_info, str):
                error_msg += _("The Peppol service that is used is likely to be %s.", participant_info)
            raise UserError(error_msg)

        edi_user = self.env['account_edi_proxy_client.user'].sudo()._register_proxy_user(company, peppol_edi_format, edi_identification)
        self.account_peppol_proxy_state = 'pending'

        # if there is an error when activating the participant below,
        # the client side is rolled back and the edi user is deleted on the client side
        # but remains on the proxy side.
        # it is important to keep these two in sync, so commit before activating.
        if not tools.config['test_enable'] and not modules.module.current_test:
            self.env.cr.commit()

        company_details = {
            'peppol_company_name': company.display_name,
            'peppol_company_vat': company.vat,
            'peppol_company_street': company.street,
            'peppol_company_city': company.city,
            'peppol_company_zip': company.zip,
            'peppol_country_code': company.country_id.code,
            'peppol_phone_number': self.account_peppol_phone_number,
            'peppol_contact_email': self.account_peppol_contact_email,
        }

        params = {
            'company_details': company_details,
            'supported_identifiers': list(company._peppol_supported_document_types()),
        }

        self._call_peppol_proxy(
            endpoint='/api/peppol/1/register_receiver',
            params=params,
            edi_user=edi_user,
        )

    @handle_demo
    def button_update_peppol_user_data(self):
        """
        Action for the user to be able to update their contact details any time
        Calls /update_user on the iap server
        """
        self.ensure_one()

        if not self.account_peppol_contact_email or not self.account_peppol_phone_number:
            raise ValidationError(_("Contact email and mobile number are required."))

        params = {
            'update_data': {
                'peppol_phone_number': self.account_peppol_phone_number,
                'peppol_contact_email': self.account_peppol_contact_email,
            }
        }

        self._call_peppol_proxy(
            endpoint='/api/peppol/1/update_user',
            params=params,
        )

    def button_cancel_peppol_registration(self):
        """
        Sets the peppol registration to canceled
        - If the user is active on the SMP, we can't just cancel it. They have to deregister.
        - 'not_registered', 'rejected', 'canceled' proxy states mean that canceling the registration
          makes no sense, so we don't do it
        - Calls the IAP server first before setting the state as canceled on the client side,
          in case they've been activated on the IAP side in the meantime
        """
        self.ensure_one()
        # check if the participant has been already registered
        self.account_peppol_edi_user._peppol_get_participant_status()
        if not tools.config['test_enable'] and not modules.module.current_test:
            self.env.cr.commit()

        if self.account_peppol_proxy_state == 'active':
            raise UserError(_("Can't cancel an active registration. Please deregister instead."))

        if self.account_peppol_proxy_state in {'not_registered', 'rejected', 'canceled'}:
            raise UserError(_(
                "Can't cancel registration with this status: %s", self.account_peppol_proxy_state
            ))

        self._call_peppol_proxy(endpoint='/api/peppol/1/cancel_peppol_registration')
        self.account_peppol_proxy_state = 'not_registered'
        self.account_peppol_edi_user.unlink()

    @handle_demo
    def button_deregister_peppol_participant(self):
        """
        Deregister the edi user from Peppol network
        """
        self.ensure_one()

        if self.account_peppol_proxy_state != 'active':
            raise UserError(_(
                "Can't deregister with this status: %s", self.account_peppol_proxy_state
            ))

        # fetch all documents and message statuses before unlinking the edi user
        # so that the invoices are acknowledged
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()
        if not tools.config['test_enable'] and not modules.module.current_test:
            self.env.cr.commit()

        self._call_peppol_proxy(endpoint='/api/peppol/1/cancel_peppol_registration')
        self.account_peppol_proxy_state = 'not_registered'
        self.account_peppol_edi_user.unlink()
