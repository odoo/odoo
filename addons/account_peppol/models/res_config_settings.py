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
    peppol_external_provider = fields.Char(related='company_id.peppol_external_provider', readonly=False)
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

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def action_open_peppol_form(self):
        view = self.env.ref('account_peppol.peppol_registration_form').sudo()
        # TODO remove in master this hack to get the branches management
        if 'use_parent_connection' not in view.arch_db:
            view.reset_arch(mode="hard")
        registration_wizard = self.env['peppol.registration'].create({'company_id': self.company_id.id})
        registration_action = registration_wizard._action_open_peppol_form(reopen=False)
        return registration_action

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
        }

    def button_peppol_register_sender_as_receiver(self):
        """Register the existing user as a receiver."""
        self.ensure_one()
        return self.env['peppol.config.wizard'].new().button_peppol_register_sender_as_receiver()

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
