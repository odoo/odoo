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
    peppol_external_provider = fields.Char(related='company_id.peppol_external_provider', readonly=False)
    peppol_use_parent_company = fields.Boolean(compute='_compute_peppol_use_parent_company')
    peppol_parent_company_name = fields.Char(related='company_id.peppol_parent_company_id.name', string="Peppol Parent Company Name")
    account_is_token_out_of_sync = fields.Boolean(related='account_peppol_edi_user.is_token_out_of_sync', readonly=False)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id.peppol_parent_company_id')
    def _compute_peppol_use_parent_company(self):
        for setting in self:
            setting.peppol_use_parent_company = bool(setting.company_id.peppol_parent_company_id)

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def action_open_peppol_form(self):
        registration_wizard = self.env['peppol.registration'].create({'company_id': self.company_id.id})
        registration_action = registration_wizard._action_open_peppol_form(reopen=False)
        return registration_action

    def button_open_peppol_config_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Advanced Peppol Configuration',
            'res_model': 'peppol.config.wizard',
            'view_mode': 'form',
            'target': 'new',
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
        self.account_peppol_edi_user._peppol_register_sender_as_receiver()
        self.account_peppol_edi_user._peppol_get_participant_status()
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
