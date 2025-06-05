# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError, ValidationError

from odoo.addons.account_peppol.tools.demo_utils import handle_demo


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_peppol_edi_user = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        string='EDI user',
        compute='_compute_account_peppol_edi_user',
    )
    account_peppol_edi_mode = fields.Selection(related='account_peppol_edi_user.edi_mode')
    account_peppol_contact_email = fields.Char(related='company_id.account_peppol_contact_email', readonly=False)
    account_peppol_eas = fields.Selection(related='company_id.peppol_eas', readonly=False)
    account_peppol_edi_identification = fields.Char(related='account_peppol_edi_user.edi_identification')
    account_peppol_endpoint = fields.Char(related='company_id.peppol_endpoint', readonly=False)
    account_peppol_migration_key = fields.Char(related='company_id.account_peppol_migration_key', readonly=False)
    account_peppol_phone_number = fields.Char(related='company_id.account_peppol_phone_number', readonly=False)
    account_peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state', readonly=False)
    account_peppol_purchase_journal_id = fields.Many2one(related='company_id.peppol_purchase_journal_id', readonly=False)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('is_account_peppol_eligible', 'account_peppol_edi_user')
    def _compute_account_peppol_mode_constraint(self):
        mode_constraint = self.env['ir.config_parameter'].sudo().get_param('account_peppol.mode_constraint')
        trial_param = self.env['ir.config_parameter'].sudo().get_param('saas_trial.confirm_token')
        self.account_peppol_mode_constraint = trial_param and 'demo' or mode_constraint or 'prod'

    @api.depends("company_id.account_edi_proxy_client_ids")
    def _compute_account_peppol_edi_user(self):
        for config in self:
            config.account_peppol_edi_user = config.company_id.account_edi_proxy_client_ids.filtered(
                lambda u: u.proxy_type == 'peppol')

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def action_open_peppol_form(self):
        registration_wizard = self.env['peppol.registration'].create({'company_id': self.company_id.id})
        registration_action = registration_wizard._action_open_peppol_form(reopen=False)
        return registration_action

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

        self.account_peppol_edi_user._call_peppol_proxy(
            endpoint='/api/peppol/1/update_user',
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

    @handle_demo
    def button_deregister_peppol_participant(self):
        """
        Deregister the edi user from Peppol network
        """
        self.ensure_one()

        if self.account_peppol_edi_user:
            self.account_peppol_edi_user._peppol_deregister_participant()
        return True

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
