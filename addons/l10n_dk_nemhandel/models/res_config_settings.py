from odoo import api, fields, models, modules, tools, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.l10n_dk_nemhandel.tools.demo_utils import handle_demo


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nemhandel_edi_user = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        compute='_compute_nemhandel_edi_user',
    )
    nemhandel_edi_mode = fields.Selection(related='nemhandel_edi_user.edi_mode')
    nemhandel_contact_email = fields.Char(related='company_id.nemhandel_contact_email', readonly=False)
    nemhandel_identifier_type = fields.Selection(related='company_id.nemhandel_identifier_type', readonly=False)
    nemhandel_identifier_value = fields.Char(related='company_id.nemhandel_identifier_value', readonly=False)
    nemhandel_edi_identification = fields.Char(string='Nemhandel identification', related='nemhandel_edi_user.edi_identification')
    nemhandel_phone_number = fields.Char(related='company_id.nemhandel_phone_number', readonly=False)
    l10n_dk_nemhandel_proxy_state = fields.Selection(related='company_id.l10n_dk_nemhandel_proxy_state', readonly=False)
    nemhandel_purchase_journal_id = fields.Many2one(related='company_id.nemhandel_purchase_journal_id', readonly=False)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends("company_id.account_edi_proxy_client_ids")
    def _compute_nemhandel_edi_user(self):
        for config in self:
            config.nemhandel_edi_user = config.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'nemhandel')

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def action_open_nemhandel_form(self):
        registration_wizard = self.env['nemhandel.registration'].create({'company_id': self.company_id.id})
        registration_action = registration_wizard._action_open_nemhandel_form(reopen=False)
        return registration_action

    @handle_demo
    def button_update_nemhandel_user_data(self):
        """
        Action for the user to be able to update their contact details any time
        Calls /update_user on the iap server
        """
        self.ensure_one()

        if not self.nemhandel_contact_email or not self.nemhandel_phone_number:
            raise ValidationError(_("Contact email and phone number are required."))

        params = {
            'update_data': {
                'nemhandel_phone_number': self.nemhandel_phone_number,
                'nemhandel_contact_email': self.nemhandel_contact_email,
            }
        }

        self.nemhandel_edi_user._call_nemhandel_proxy(
            endpoint='/api/nemhandel/1/update_user',
            params=params,
        )
        return True

    @handle_demo
    def button_deregister_nemhandel_participant(self):
        """
        Deregister the edi user from Nemhandel network
        """
        self.ensure_one()

        if self.nemhandel_edi_user:
            self.nemhandel_edi_user._nemhandel_deregister_participant()
        return True
