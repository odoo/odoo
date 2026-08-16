# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError, ValidationError

from odoo.addons.account_peppol.tools.demo_utils import handle_demo


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
    peppol_purchase_journal_required = fields.Boolean(compute='_compute_peppol_purchase_journal_required')
    peppol_use_parent_company = fields.Boolean(compute='_compute_peppol_use_parent_company')
    peppol_parent_company_name = fields.Char(compute='_compute_peppol_use_parent_company')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id.peppol_parent_company_id')
    def _compute_peppol_use_parent_company(self):
        for setting in self:
            setting.peppol_use_parent_company = (
                setting.company_id != setting.company_id.peppol_parent_company_id
                and setting.company_id.peppol_can_send
                and setting.company_id.peppol_parent_company_id.peppol_can_send
            )
            if setting.peppol_use_parent_company:
                setting.peppol_parent_company_name = setting.company_id.peppol_parent_company_id.name
            else:
                setting.peppol_parent_company_name = None

    @api.depends('is_account_peppol_eligible', 'account_peppol_edi_user')
    def _compute_account_peppol_mode_constraint(self):
        mode_constraint = self.env['ir.config_parameter'].sudo().get_param('account_peppol.mode_constraint')
        trial_param = self.env['ir.config_parameter'].sudo().get_param('saas_trial.confirm_token')
        self.account_peppol_mode_constraint = trial_param and 'demo' or mode_constraint or 'prod'

    @api.depends('account_peppol_proxy_state')
    def _compute_peppol_purchase_journal_required(self):
        for config in self:
            config.peppol_purchase_journal_required = config.account_peppol_proxy_state in ('smp_registration', 'receiver')

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def action_open_peppol_form(self):
        registration_wizard = self.env['peppol.registration'].create({'company_id': self.company_id.id})
        registration_action = registration_wizard._action_open_peppol_form(reopen=False)
        return registration_action

    def _get_peppol_proxy_type(self):
        self.ensure_one()
<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
        return self.account_peppol_edi_user.proxy_type
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
        if self.account_peppol_eas != '0225':
            return

        # We use an explicit search instead of `_get` because `_get_id` is cached
        # via ormcache in 17.0 and will not return accurate results after `base.action_view_base_module_update`.
        # This issue is resolved in 18.0.
        pdp_module = self.env['ir.module.module'].search([('name', '=', 'l10n_fr_pdp')], limit=1)
        if pdp_module and pdp_module.state != 'installed':
            redirect_action = pdp_module._get_records_action()
            message = _(
                "If you want to register for the French e-invoicing, first install the PDP module: France - E-Invoicing (Approved Platform).",
            )
            redirect_button_text = _("Install module")
        else:
            redirect_action = self.env.ref('base.action_view_base_module_update').id
            message = _(
                "If you want to register for the French e-invoicing, first install the PDP module: France - E-Invoicing (Approved Platform).\n"
                "The module was not found. Please update the available apps first.",
            )
            redirect_button_text = _("Update Apps List")

        raise RedirectWarning(
                message=message,
                action=redirect_action,
                button_text=redirect_button_text,
            )

    @handle_demo
    def button_create_peppol_proxy_user(self):
        """
        The first step of the Peppol onboarding.
        - Creates an EDI proxy user on the iap side, then the client side
        - Calls /activate_participant to mark the EDI user as peppol user
        - If endpoint is already on Peppol, can register as sender-only after explicit confirmation
        """
        self.ensure_one()
        self._ensure_pdp_not_sent_through_peppol()
        company = self.company_id

        if self.account_peppol_proxy_state != 'not_registered':
            raise UserError(_('Cannot register a user with a %s application', self.account_peppol_proxy_state))

        blocking_proxy_types = set(self.env['account_edi_proxy_client.user']._get_peppol_proxy_types()) - {'peppol'}
        blocking_user = self.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type in blocking_proxy_types)
        if blocking_user:
            blocking_proxy_type = dict(blocking_user._fields['proxy_type']._description_selection(self.env))[blocking_user[:1].proxy_type]
            raise UserError(_("A connection to '%s' already exists.", blocking_proxy_type))

        if not self.account_peppol_phone_number:
            raise ValidationError(_("Please enter a mobile number to verify your application."))
        if not self.account_peppol_contact_email:
            raise ValidationError(_("Please enter a primary contact email to verify your application."))

        edi_proxy_client = self.env['account_edi_proxy_client.user']
        edi_identification = edi_proxy_client._get_proxy_identification(company, 'peppol')

        recovered_edi_users = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(company, peppol_identifier=edi_identification)
        if recovered_edi_users:
            return

        company.partner_id._check_peppol_eas()

        if self._use_parent_connection(company):
            edi_user = edi_proxy_client.sudo()._register_proxy_user(company, 'peppol', self.account_peppol_edi_mode)

            if not tools.config['test_enable'] and not modules.module.current_test:
                self.env.cr.commit()

            self._call_peppol_proxy(
                endpoint=edi_user._get_peppol_proxy_endpoint('1/register_sender'),
                params={'company_details': edi_user._get_company_details()},
                edi_user=edi_user,
            )

            self.account_peppol_proxy_state = 'sender'

            return

        participant_info = company.partner_id._check_peppol_participant_exists(edi_identification, check_company=True)
        should_offer_sender_only = bool(participant_info and not self.account_peppol_migration_key)

        if should_offer_sender_only and not self.env.context.get('account_peppol_register_sender_only'):
            error_msg = _(
                "A participant with these details has already been registered on the network. "
                "If you continue, Odoo will register this company as sender only."
            )

            if isinstance(participant_info, str):
                error_msg += _("The Peppol service that is used is likely to be %s.", participant_info)
            raise EndpointAlreadyRegisteredError(error_msg)

        edi_user = edi_proxy_client.sudo()._register_proxy_user(company, 'peppol', self.account_peppol_edi_mode)

        # if there is an error when activating the participant below,
        # the client side is rolled back and the edi user is deleted on the client side
        # but remains on the proxy side.
        # it is important to keep these two in sync, so commit before activating.
        if not tools.config['test_enable'] and not modules.module.current_test:
            self.env.cr.commit()

        self.account_peppol_proxy_state = 'not_verified'
        if should_offer_sender_only:
            self._call_peppol_proxy(
                endpoint=edi_user._get_peppol_proxy_endpoint('1/register_sender'),
                params={'company_details': edi_user._get_company_details()},
                edi_user=edi_user,
            )
            self.account_peppol_proxy_state = 'sender'
        else:
            params = {
                'migration_key': self.account_peppol_migration_key,
                'company_details': edi_user._get_company_details(),
                'supported_identifiers': list(edi_user.company_id._peppol_supported_document_types()),
            }

            self._call_peppol_proxy(
                endpoint=edi_user._get_peppol_proxy_endpoint('1/activate_participant'),
                params=params,
                edi_user=edi_user,
            )
        # once we sent the migration key over, we don't need it
        # but we need the field for future in case the user decided to migrate away from Odoo
        self.account_peppol_migration_key = False

    @handle_demo
    def button_create_peppol_proxy_user_sender_only(self):
        self.ensure_one()
        return self.with_context(account_peppol_register_sender_only=True).button_create_peppol_proxy_user()

    def _check_mandatory_peppol_user_data(self):
        self.ensure_one()
        if not self.account_peppol_contact_email or not self.account_peppol_phone_number:
            raise ValidationError(_("Contact email and mobile number are required."))
=======
        if self.account_peppol_eas != '0225':
            return

        # We use an explicit search instead of `_get` because `_get_id` is cached
        # via ormcache in 17.0 and will not return accurate results after `base.action_view_base_module_update`.
        # This issue is resolved in 18.0.
        pdp_module = self.env['ir.module.module'].search([('name', '=', 'l10n_fr_pdp')], limit=1)
        if pdp_module and pdp_module.state != 'installed':
            redirect_action = pdp_module._get_records_action()
            message = _(
                "If you want to register for the French e-invoicing, first install the PDP module: France - E-Invoicing (Approved Platform).",
            )
            redirect_button_text = _("Install module")
        else:
            redirect_action = self.env.ref('base.action_view_base_module_update').id
            message = _(
                "If you want to register for the French e-invoicing, first install the PDP module: France - E-Invoicing (Approved Platform).\n"
                "The module was not found. Please update the available apps first.",
            )
            redirect_button_text = _("Update Apps List")

        raise RedirectWarning(
                message=message,
                action=redirect_action,
                button_text=redirect_button_text,
            )

    @handle_demo
    def button_create_peppol_proxy_user(self):
        """
        The first step of the Peppol onboarding.
        - Creates an EDI proxy user on the iap side, then the client side
        - Calls /activate_participant to mark the EDI user as peppol user
        - If endpoint is already on Peppol, can register as sender-only after explicit confirmation
        """
        # DEPRECATED, USE button_register_with_kyc
        self.ensure_one()
        self._ensure_pdp_not_sent_through_peppol()
        company = self.company_id

        if self.account_peppol_proxy_state != 'not_registered':
            raise UserError(_('Cannot register a user with a %s application', self.account_peppol_proxy_state))

        blocking_proxy_types = set(self.env['account_edi_proxy_client.user']._get_peppol_proxy_types()) - {'peppol'}
        blocking_user = self.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type in blocking_proxy_types)
        if blocking_user:
            blocking_proxy_type = dict(blocking_user._fields['proxy_type']._description_selection(self.env))[blocking_user[:1].proxy_type]
            raise UserError(_("A connection to '%s' already exists.", blocking_proxy_type))

        if not self.account_peppol_phone_number:
            raise ValidationError(_("Please enter a mobile number to verify your application."))
        if not self.account_peppol_contact_email:
            raise ValidationError(_("Please enter a primary contact email to verify your application."))

        edi_proxy_client = self.env['account_edi_proxy_client.user']
        edi_identification = edi_proxy_client._get_proxy_identification(company, 'peppol')

        recovered_edi_users = self.env['account_edi_proxy_client.user']._try_recover_peppol_proxy_users(company, peppol_identifier=edi_identification)
        if recovered_edi_users:
            return

        company.partner_id._check_peppol_eas()

        if self._use_parent_connection(company):
            edi_user = edi_proxy_client.sudo()._register_proxy_user(company, 'peppol', self.account_peppol_edi_mode)

            if not tools.config['test_enable'] and not modules.module.current_test:
                self.env.cr.commit()

            self._call_peppol_proxy(
                endpoint=edi_user._get_peppol_proxy_endpoint('1/register_sender'),
                params={'company_details': edi_user._get_company_details()},
                edi_user=edi_user,
            )

            self.account_peppol_proxy_state = 'sender'

            return

        participant_info = company.partner_id._check_peppol_participant_exists(edi_identification, check_company=True)
        should_offer_sender_only = bool(participant_info and not self.account_peppol_migration_key)

        if should_offer_sender_only and not self.env.context.get('account_peppol_register_sender_only'):
            error_msg = _(
                "A participant with these details has already been registered on the network. "
                "If you continue, Odoo will register this company as sender only."
            )

            if isinstance(participant_info, str):
                error_msg += _("The Peppol service that is used is likely to be %s.", participant_info)
            raise EndpointAlreadyRegisteredError(error_msg)

        edi_user = edi_proxy_client.sudo()._register_proxy_user(company, 'peppol', self.account_peppol_edi_mode)

        # if there is an error when activating the participant below,
        # the client side is rolled back and the edi user is deleted on the client side
        # but remains on the proxy side.
        # it is important to keep these two in sync, so commit before activating.
        if not tools.config['test_enable'] and not modules.module.current_test:
            self.env.cr.commit()

        self.account_peppol_proxy_state = 'not_verified'
        if should_offer_sender_only:
            self._call_peppol_proxy(
                endpoint=edi_user._get_peppol_proxy_endpoint('1/register_sender'),
                params={'company_details': edi_user._get_company_details()},
                edi_user=edi_user,
            )
            self.account_peppol_proxy_state = 'sender'
        else:
            params = {
                'migration_key': self.account_peppol_migration_key,
                'company_details': edi_user._get_company_details(),
                'supported_identifiers': list(edi_user.company_id._peppol_supported_document_types()),
            }

            self._call_peppol_proxy(
                endpoint=edi_user._get_peppol_proxy_endpoint('1/activate_participant'),
                params=params,
                edi_user=edi_user,
            )
        # once we sent the migration key over, we don't need it
        # but we need the field for future in case the user decided to migrate away from Odoo
        self.account_peppol_migration_key = False

    @handle_demo
    def button_create_peppol_proxy_user_sender_only(self):
        self.ensure_one()
        return self.with_context(account_peppol_register_sender_only=True).button_register_with_kyc()

    def _check_mandatory_peppol_user_data(self):
        self.ensure_one()
        if not self.account_peppol_contact_email or not self.account_peppol_phone_number:
            raise ValidationError(_("Contact email and mobile number are required."))
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

    @handle_demo
    def button_update_peppol_user_data(self):
        """
        Action for the user to be able to update their contact details any time
        Calls /update_user on the iap server
        """
        self.ensure_one()

        if not self.account_peppol_contact_email:
            raise ValidationError(self.env._("A contact email is required."))

        params = {
            'update_data': {
                **({'peppol_phone_number': self.account_peppol_phone_number} if self.account_peppol_phone_number else {}),
                'peppol_contact_email': self.account_peppol_contact_email,
            }
        }

        self.account_peppol_edi_user._call_peppol_proxy(
            endpoint=self.account_peppol_edi_user._get_peppol_proxy_endpoint('1/update_user'),
            params=params,
        )
        return True

    @handle_demo
    def button_peppol_smp_registration(self):
        """
        The second (optional) step in Peppol registration.
        The user can choose to become a Receiver and officially register on the Peppol
        network, i.e. receive documents from other Peppol participants.
        """
        self.ensure_one()
        self.account_peppol_edi_user._peppol_register_sender_as_receiver()
        if self.account_peppol_proxy_state == 'smp_registration':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Registered to receive documents via Peppol."),
                    'type': 'success',
                    'message': _("Your registration on Peppol network should be activated within a day. The updated status will be visible in Settings."),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        return True

    def button_migrate_peppol_registration(self):
        """
        Migrates AWAY from Odoo's SMP.
        If the user is a receiver, they need to request a migration key, generated on the IAP server.
        The migration key is then displayed in Peppol settings.
        Currently, reopening after migrating away is not supported.
        """
        raise UserError(_("This feature is deprecated. Contact Odoo support if you need a migration key."))

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

    @handle_demo
    def button_deregister_peppol_participant(self):
        """
        Deregister the edi user from Peppol network
        """
        self.ensure_one()

        if self.account_peppol_edi_user:
            self.account_peppol_edi_user._peppol_deregister_participant()
        else:
            self.company_id._reset_peppol_configuration()
        return True

    def button_peppol_reset_to_sender(self):
        """Reset the participant back to sender and deregister it from the SMP"""
        self.ensure_one()

<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf
        if self.account_peppol_edi_user:
            self.account_peppol_edi_user._peppol_deregister_participant_to_sender()
        return True
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
    def action_open_peppol_form(self):
        # There is no form / wizard for peppol registration in 17.0 (only in 18.0+)
        return self.button_create_peppol_proxy_user()
=======
    def action_open_peppol_form(self):
        # There is no form / wizard for peppol registration in 17.0 (only in 18.0+)
        return self.button_register_with_kyc()
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a

    def button_peppol_reregister(self):
        self.ensure_one()
        if self.country_code == 'FR' and self.env['ir.module.module']._get('l10n_fr_pdp').state != 'installed':
            raise UserError(self.env._("Please install the 'France - E-Invoicing (Approved Platform)' module (l10n_fr_pdp) first"))
        self.button_deregister_peppol_participant()
        self.company_id._reset_peppol_configuration()
        return self.action_open_peppol_form()
<<<<<<< 7950c5b47b8b8315a0eff73a1d242fdc72dddcdf

    # Note: Deprecated; the button is permanently invisible.
    # Disabling services can lead to complicance issues and is not necessary
    # since all existing services should just work.
    def button_account_peppol_configure_services(self):
        wizard = self.env['account_peppol.service.wizard'].create({
            'edi_user_id': self.account_peppol_edi_user.id,
            'service_json': self.account_peppol_edi_user._peppol_get_services().get('services'),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configure your peppol services',
            'res_model': 'account_peppol.service.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.model
    def _get_pdp_module_info(self):
        pdp_module = self.env['ir.module.module'].sudo()._get('l10n_fr_pdp')  # avoid returning it since it is sudoed
        module_name = self.env._("France - E-Invoicing (Approved Platform)")
        if pdp_module:
            action = pdp_module._get_records_action()
            action_name = self.env._("Go to module")
            warning = self.env._("To use the Approved Platform for French E-Invoicing install the module '%s'.", module_name)
        else:
            action = self.env.ref('base.action_view_base_module_update').id
            action_name = self.env._("Update App List")
            warning = self.env._("To use the Approved Platform for French E-Invoicing install the module '%s'.\n"
                                 "The module was not found. Please update the app list first.",
                                 module_name)
        return {
            'is_installed': pdp_module and pdp_module.state == 'installed',
            'module_name': module_name,
            'action': action,
            'action_name': action_name,
            'warning_message': warning,
        }
||||||| 89081cc015d517880d3cadc2d61c278b4b379502
=======

    def button_register_with_kyc(self):
        self.ensure_one()
        self._ensure_pdp_not_sent_through_peppol()
        company = self.company_id

        if self.account_peppol_proxy_state != 'not_registered':
            raise UserError(_('Cannot register a user with a %s application', self.account_peppol_proxy_state))

        edi_proxy_client = self.env['account_edi_proxy_client.user']
        blocking_proxy_types = set(edi_proxy_client._get_peppol_proxy_types()) - {'peppol'}
        blocking_user = company.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type in blocking_proxy_types)
        if blocking_user:
            blocking_proxy_type = dict(blocking_user._fields['proxy_type']._description_selection(self.env))[blocking_user[:1].proxy_type]
            raise UserError(_("A connection to '%s' already exists.", blocking_proxy_type))

        self._check_mandatory_peppol_user_data()
        company.partner_id._check_peppol_eas()

        edi_identification = edi_proxy_client._get_proxy_identification(company, 'peppol')
        recovered_edi_users = edi_proxy_client._try_recover_peppol_proxy_users(company, peppol_identifier=edi_identification)
        if recovered_edi_users:
            return {'type': 'ir.actions.client', 'tag': 'reload'}

        participant_info = (
            not self._use_parent_connection(company)
            and company.partner_id._check_peppol_participant_exists(edi_identification, check_company=True)
        )
        if (
            participant_info
            and not self.account_peppol_migration_key
            and not self.env.context.get('account_peppol_register_sender_only')
        ):
            error_msg = _(
                "A participant with these details has already been registered on the network. "
                "If you continue, Odoo will register this company as sender only."
            )

            if isinstance(participant_info, str):
                error_msg += _("The Peppol service that is used is likely to be %s.", participant_info)
            raise EndpointAlreadyRegisteredError(error_msg)

        # archive before can_connect because _get_peppol_edi_mode() reads the active user
        edi_proxy_client.sudo().search([
            ('company_id', '=', company.id),
            ('proxy_type', '=', 'peppol'),
        ]).active = False
        edi_proxy_client.flush_model(['active'])

        authorization_url = self.env['res.company']._peppol_select_kyc_url(
            company._peppol_can_connect(edi_identification.lower())
        )

        if authorization_url:
            # redirect to IAP KYC link (that will redirect back to here thru callback)
            return {'type': 'ir.actions.act_url', 'url': authorization_url, 'target': 'self'}

        company._peppol_create_connection(edi_identification.lower())  # no auth, IAP will authorize connection directly
        return {'type': 'ir.actions.client', 'tag': 'reload'}
>>>>>>> 0abc2fba1dcb90099cc1a455d086f1bcf7bd934a
