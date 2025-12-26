from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

#from odoo.addons.l10n_dk_nemhandel.tools.demo_utils import handle_demo


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    eracun_edi_user = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        compute='_compute_eracun_edi_user',
    )
    eracun_edi_mode = fields.Selection(string='eRacun EDI operating mode', related='eracun_edi_user.edi_mode')
    eracun_contact_email = fields.Char(related='company_id.eracun_contact_email', readonly=False)
    eracun_identifier_type = fields.Selection(related='company_id.eracun_identifier_type', readonly=False)
    eracun_identifier_value = fields.Char(related='company_id.eracun_identifier_value', readonly=False)
    eracun_edi_identification = fields.Char(string='eRacun identification', related='eracun_edi_user.edi_identification')
    l10n_hr_eracun_proxy_state = fields.Selection(related='company_id.l10n_hr_eracun_proxy_state', readonly=False)
    eracun_purchase_journal_id = fields.Many2one(related='company_id.eracun_purchase_journal_id', readonly=False)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends("company_id.account_edi_proxy_client_ids")
    def _compute_eracun_edi_user(self):
        for config in self:
            config.eracun_edi_user = config.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'eracun')

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    # Requires a corresponding form to be created
    def action_open_eracun_form(self):
        self.ensure_one()
        registration_wizard = self.env['eracun.registration'].create({'company_id': self.company_id.id})
        registration_action = registration_wizard._action_open_eracun_form(reopen=False)
        return registration_action

    #@handle_demo
    def button_update_eracun_user_data(self):
        """
        Action for the user to be able to update their contact details any time
        Calls /update_user on the iap server
        """
        self.ensure_one()

        if not self.eracun_contact_email:
            raise ValidationError(_("Contact email is required"))

        self.eracun_edi_user._call_eracun_proxy(
            endpoint='/api/eracun/1/update_user',
            params={
                'update_data': {
                    'eracun_contact_email': self.eracun_contact_email,
                },
            },
        )
        return True

    #@handle_demo
    def button_deregister_eracun_participant(self):
        """
        Deregister the edi user from eRacun network
        """
        self.ensure_one()

        if self.eracun_edi_user:
            self.eracun_edi_user._eracun_deregister_participant()
        return True
