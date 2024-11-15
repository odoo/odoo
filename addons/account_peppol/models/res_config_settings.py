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

    def button_peppol_update_user_data(self):
        """Update contact details of the Peppol user."""
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

    def button_peppol_migrate_away(self):
        """Migrates AWAY from Odoo's SMP.
        If the user is a receiver, they need to request a migration key, generated on the IAP server.
        The migration key is then displayed in Peppol settings.
        Currently, reopening after migrating away is not supported.
        """
        self.ensure_one()
        if self.account_peppol_proxy_state != 'receiver':
            raise UserError(_("Can't migrate unless registered to receive documents."))

        self.account_peppol_edi_user._peppol_migrate_registration()
        return True

    def button_peppol_unregister(self):
        """Unregister the user from Peppol network."""
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
