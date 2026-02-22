from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.l10n_fr_pdp.tools.demo_utils import handle_demo


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_fr_pdp_edi_user = fields.Many2one(related='company_id.pdp_edi_user')
    l10n_fr_pdp_edi_mode = fields.Selection(related='l10n_fr_pdp_edi_user.edi_mode', string="PDP EDI Operating Mode")
    l10n_fr_pdp_contact_email = fields.Char(related='company_id.pdp_contact_email', readonly=False)
    l10n_fr_pdp_phone_number = fields.Char(related='company_id.pdp_phone_number', readonly=False)
    l10n_fr_pdp_edi_identification = fields.Char(related='l10n_fr_pdp_edi_user.edi_identification', string="PDP EDI identification")
    l10n_fr_pdp_proxy_state = fields.Selection(related='company_id.l10n_fr_pdp_proxy_state', readonly=False)
    l10n_fr_pdp_purchase_journal_id = fields.Many2one(related='company_id.pdp_purchase_journal_id', readonly=False)

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def action_open_pdp_form(self):
        registration_wizard = self.env['pdp.registration'].create({'company_id': self.company_id.id})
        return registration_wizard._action_open_pdp_form(reopen=False)

    @handle_demo
    def button_update_pdp_user_data(self):
        """
        Action for the user to be able to update their contact details any time.
        Calls /update_user on the iap server.
        """
        self.ensure_one()

        if not self.l10n_fr_pdp_contact_email or not self.l10n_fr_pdp_phone_number:
            raise ValidationError(_("Contact email and mobile number are required."))

        params = {
            'update_data': {
                'peppol_phone_number': self.l10n_fr_pdp_phone_number,
                'peppol_contact_email': self.l10n_fr_pdp_contact_email,
            }
        }

        self.l10n_fr_pdp_edi_user._call_pdp_proxy(
            endpoint='/api/pdp/1/update_user',
            params=params,
        )
        return True

    @handle_demo
    def button_deregister_pdp_participant(self):
        """
        Deregister the edi user from PDP network
        """
        self.ensure_one()

        if self.l10n_fr_pdp_edi_user:
            self.l10n_fr_pdp_edi_user._pdp_deregister_participant()
        return True
