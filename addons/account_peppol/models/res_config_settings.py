from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_peppol_edi_user = fields.Many2one(related='company_id.account_peppol_edi_user')
    account_peppol_edi_mode = fields.Selection(related='account_peppol_edi_user.edi_mode')
    account_peppol_contact_email = fields.Char(related='company_id.account_peppol_contact_email', readonly=False)
    account_peppol_eas = fields.Selection(related='company_id.peppol_eas', readonly=False)
    account_peppol_edi_identification = fields.Char(related='account_peppol_edi_user.edi_identification')
    account_peppol_endpoint = fields.Char(related='company_id.peppol_endpoint', readonly=False)
    account_peppol_migration_key = fields.Char(related='company_id.account_peppol_migration_key', readonly=False)
    account_peppol_phone_number = fields.Char(related='company_id.account_peppol_phone_number', readonly=False)
    account_peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state', readonly=False)
    account_peppol_purchase_journal_id = fields.Many2one(related='company_id.peppol_purchase_journal_id', readonly=False)
<<<<<<< ecd3897728f2dcb52f30d365a4baab1396a26459
    peppol_external_provider = fields.Char(related='company_id.peppol_external_provider', readonly=False)
    peppol_use_parent_company = fields.Boolean(compute='_compute_peppol_use_parent_company')
    peppol_parent_company_name = fields.Char(related='company_id.peppol_parent_company_id.name', string="Peppol Parent Company Name")
    account_is_token_out_of_sync = fields.Boolean(related='account_peppol_edi_user.is_token_out_of_sync', readonly=False)
||||||| 13e8b462e74f144e085492857bfaa7b0d1f88f93
    account_peppol_verification_code = fields.Char(related='account_peppol_edi_user.peppol_verification_code', readonly=False)
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
    account_peppol_mode_constraint = fields.Selection(
        selection=[('demo', 'Demo'), ('test', 'Test'), ('prod', 'Live')],
        compute='_compute_account_peppol_mode_constraint',
        help="Using the config params, this field specifies which edi modes may be selected from the UI"
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
            edi_user = self.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol')

        params = params or {}
        try:
            response = edi_user._make_request(
                f"{edi_user._get_server_url()}{endpoint}",
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
=======
    account_peppol_verification_code = fields.Char(related='account_peppol_edi_user.peppol_verification_code', readonly=False)
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
    account_peppol_mode_constraint = fields.Selection(
        selection=[('demo', 'Demo'), ('test', 'Test'), ('prod', 'Live')],
        compute='_compute_account_peppol_mode_constraint',
        help="Using the config params, this field specifies which edi modes may be selected from the UI"
    )
    peppol_use_parent_company = fields.Boolean(compute='_compute_peppol_use_parent_company')

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
            edi_user = self.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol')

        params = params or {}
        try:
            response = edi_user._make_request(
                f"{edi_user._get_server_url()}{endpoint}",
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
>>>>>>> 6f3b9a3dcabe936bd66dd5ad5cc6805135093504

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id.peppol_parent_company_id')
    def _compute_peppol_use_parent_company(self):
        for setting in self:
            setting.peppol_use_parent_company = bool(setting.company_id.peppol_parent_company_id)

    @api.depends('account_peppol_edi_user', 'company_id.peppol_eas', 'company_id.peppol_endpoint')
    def _compute_peppol_use_parent_company(self):
        self.peppol_use_parent_company = False
        for config in self:
            if config.account_peppol_edi_user:
                for parent_company in config.company_id.parent_ids[::-1][1:]:
                    if all((
                            config.company_id.peppol_eas,
                            config.company_id.peppol_endpoint,
                            config.company_id.peppol_eas == parent_company.peppol_eas,
                            config.company_id.peppol_endpoint == parent_company.peppol_endpoint,
                    )):
                        config.peppol_use_parent_company = True
                        break

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

<<<<<<< ecd3897728f2dcb52f30d365a4baab1396a26459
    def action_open_peppol_form(self):
        registration_wizard = self.env['peppol.registration'].create({'company_id': self.company_id.id})
        registration_action = registration_wizard._action_open_peppol_form(reopen=False)
        return registration_action
||||||| 13e8b462e74f144e085492857bfaa7b0d1f88f93
    @handle_demo
    def button_create_peppol_proxy_user(self):
        """
        The first step of the Peppol onboarding.
        - Creates an EDI proxy user on the iap side, then the client side
        - Calls /activate_participant to mark the EDI user as peppol user
        """
        self.ensure_one()
=======
    @handle_demo
    def button_create_peppol_proxy_user(self):
        """
        The first step of the Peppol onboarding.
        - Creates an EDI proxy user on the iap side, then the client side
        - Calls /activate_participant to mark the EDI user as peppol user
        """
        self.ensure_one()
        company = self.company_id
>>>>>>> 6f3b9a3dcabe936bd66dd5ad5cc6805135093504

<<<<<<< ecd3897728f2dcb52f30d365a4baab1396a26459
    def button_open_peppol_config_wizard(self):
        view = self.env.ref('account_peppol.peppol_config_wizard_form').sudo()
        # TODO remove in master this hack to have the possibility of being only a sender
        if 'button_peppol_reset_to_sender' not in view.arch_db:
            view.reset_arch(mode="hard")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Advanced Peppol Configuration',
            'res_model': 'peppol.config.wizard',
            'view_mode': 'form',
            'target': 'new',
||||||| 13e8b462e74f144e085492857bfaa7b0d1f88f93
        if self.account_peppol_proxy_state != 'not_registered':
            raise UserError(
                _('Cannot register a user with a %s application', self.account_peppol_proxy_state))

        if not self.account_peppol_phone_number:
            raise ValidationError(_("Please enter a mobile number to verify your application."))
        if not self.account_peppol_contact_email:
            raise ValidationError(_("Please enter a primary contact email to verify your application."))

        company = self.company_id
        edi_proxy_client = self.env['account_edi_proxy_client.user']
        edi_identification = edi_proxy_client._get_proxy_identification(company, 'peppol')

        recovered_edi_users = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(company, peppol_identifier=edi_identification)
        if recovered_edi_users:
            return

        company.partner_id._check_peppol_eas()

        if (
            (participant_info := company.partner_id._check_peppol_participant_exists(edi_identification, check_company=True))
            and not self.account_peppol_migration_key
        ):
            error_msg = _(
                "A participant with these details has already been registered on the network. "
                "If you have previously registered to a Peppol service, please deregister."
            )

            if isinstance(participant_info, str):
                error_msg += _("The Peppol service that is used is likely to be %s.", participant_info)
            raise UserError(error_msg)

        edi_user = edi_proxy_client.sudo()._register_proxy_user(company, 'peppol', self.account_peppol_edi_mode)
        self.account_peppol_proxy_state = 'not_verified'

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
=======
        if self.account_peppol_proxy_state != 'not_registered':
            raise UserError(
                _('Cannot register a user with a %s application', self.account_peppol_proxy_state))

        if not self.account_peppol_phone_number:
            raise ValidationError(_("Please enter a mobile number to verify your application."))
        if not self.account_peppol_contact_email:
            raise ValidationError(_("Please enter a primary contact email to verify your application."))

        for parent_company in company.parent_ids[::-1][1:]:
            if all((
                parent_company.sudo().account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol'),  # `sudo` needed otherwise empty from no access right
                parent_company.peppol_eas == company.peppol_eas,
                parent_company.peppol_endpoint == company.peppol_endpoint,
            )):
                # In 17.0 branch peppol support, we strictly restrict branches from registering their own peppol connection IF
                # their peppol identification is already used by their parent. This is because in order to send by peppol in
                # 17.0, you must also be a receiver. However, we can't register as receiver if a receiver participant with
                # same identification is already registered on the peppol network (which, in the database means, the parent
                # already registered as a receiver).
                raise ValidationError(_(
                    "This peppol identification is already used by %(parent_name)s. Please use something else.",
                    parent_name=parent_company.name,
                ))

        edi_proxy_client = self.env['account_edi_proxy_client.user']
        edi_identification = edi_proxy_client._get_proxy_identification(company, 'peppol')

        recovered_edi_users = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(company, peppol_identifier=edi_identification)
        if recovered_edi_users:
            return

        company.partner_id._check_peppol_eas()

        if (
            (participant_info := company.partner_id._check_peppol_participant_exists(edi_identification, check_company=True))
            and not self.account_peppol_migration_key
        ):
            error_msg = _(
                "A participant with these details has already been registered on the network. "
                "If you have previously registered to a Peppol service, please deregister."
            )

            if isinstance(participant_info, str):
                error_msg += _("The Peppol service that is used is likely to be %s.", participant_info)
            raise UserError(error_msg)

        edi_user = edi_proxy_client.sudo()._register_proxy_user(company, 'peppol', self.account_peppol_edi_mode)
        self.account_peppol_proxy_state = 'not_verified'

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
>>>>>>> 6f3b9a3dcabe936bd66dd5ad5cc6805135093504
        }

    def button_peppol_disconnect_branch_from_parent(self):
        self.ensure_one()
        previous_parent_company_name = self.company_id.peppol_parent_company_id.name
        self.account_peppol_edi_user._peppol_deregister_participant()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': None,
                'type': 'success',
                'message': _("Disconnected this branch company peppol configuration from %s.", previous_parent_company_name),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def button_peppol_register_sender_as_receiver(self):
        """Register the existing user as a receiver."""
        self.ensure_one()
        return self.env['peppol.config.wizard'].new().button_peppol_register_sender_as_receiver()

    def button_reconnect_this_database(self):
        """Re-establish an out-of-sync connection"""
        self.ensure_one()
        self.account_peppol_edi_user._peppol_out_of_sync_reconnect_this_database()

    def button_disconnect_this_database(self):
        """Disconnect the current database from the Peppol network.
        This does not delete or affect the IAP connection, which will remain intact.
        So don't use this to deregister the participant/connection.
        """
        self.ensure_one()
        self.account_peppol_edi_user._peppol_out_of_sync_disconnect_this_database()
