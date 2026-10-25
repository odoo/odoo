from odoo import api, fields, models


class PeppolConfigWizard(models.TransientModel):
    _name = 'pdp.config.wizard'
    _description = "Peppol Configuration Wizard"

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    account_peppol_edi_user = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        compute='_compute_account_peppol_edi_user',
    )
    account_peppol_edi_identification = fields.Char(related='account_peppol_edi_user.edi_identification')
    account_peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state', readonly=False)
    account_peppol_contact_email = fields.Char(related='company_id.account_peppol_contact_email', readonly=False, required=True)

    @api.depends('company_id')
    def _compute_account_peppol_edi_user(self):
        for wizard in self:
            wizard.account_peppol_edi_user = wizard.company_id.account_edi_proxy_client_ids.filtered(
                lambda u: u.proxy_type in self.env['account_edi_proxy_client.user']._get_peppol_proxy_types())

    def _action_open(self):
        return self._get_records_action(
            name=self.env._("Advanced E-Invoicing Configuration"),
            target='new',
        )

    def button_sync_form_with_peppol_proxy(self):
        """Update the peppol contact email on IAP.
        Note: The service configuration is DEPRECATED / hidden in the view.
        Disabling services can lead to complicance issues and is not necessary
        since all existing services should just work."""
        self.ensure_one()

        # Update email unconditionally. account_peppol_contact_email is a related field so changes can't be detected
        params = {
            'update_data': {
                'peppol_contact_email': self.account_peppol_contact_email,
            }
        }
        self.account_peppol_edi_user._call_peppol_proxy(
            endpoint=self.account_peppol_edi_user._get_peppol_proxy_endpoint('1/update_user'),
            params=params,
        )

        return True

    def button_peppol_unregister(self):
        """Unregister the user from Peppol network."""
        self.ensure_one()

        if self.account_peppol_edi_user:
            self.account_peppol_edi_user._peppol_deregister_participant()
        else:
            self.company_id._reset_peppol_configuration()
        return True
