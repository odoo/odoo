from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_hr_mer_connection_state = fields.Selection(related='company_id.l10n_hr_mer_connection_state')
    l10n_hr_mer_connection_mode = fields.Selection(related='company_id.l10n_hr_mer_connection_mode', readonly=False)

    l10n_hr_mer_username = fields.Char(related='company_id.l10n_hr_mer_username', readonly=False)
    l10n_hr_mer_password = fields.Char(related='company_id.l10n_hr_mer_password', readonly=False)
    l10n_hr_mer_company_ident = fields.Char(related='company_id.l10n_hr_mer_company_ident', readonly=False)
    l10n_hr_mer_company_bu = fields.Char(related='company_id.partner_id.l10n_hr_business_unit_code', readonly=False)
    l10n_hr_mer_software_ident = fields.Char(related='company_id.l10n_hr_mer_software_ident', readonly=False)
    l10n_hr_mer_purchase_journal_id = fields.Many2one(related='company_id.l10n_hr_mer_purchase_journal_id', readonly=False)

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def button_l10n_hr_activate_mojeracun(self):
        self.ensure_one()
        self.company_id._l10n_hr_activate_mojeracun()

    def button_l10n_hr_deactivate_mojeracun(self):
        self.ensure_one()
        self.company_id.l10n_hr_mer_connection_state = 'inactive'
