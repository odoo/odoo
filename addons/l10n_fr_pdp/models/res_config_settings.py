from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # DEPRECATED - was for the pre-prod phase
    l10n_fr_pdp_pilot_phase = fields.Boolean(
        compute='_compute_l10n_fr_pdp_pilot_phase',
        inverse='_inverse_l10n_fr_pdp_pilot_phase',
        string="Pilot Phase",
        help="Participate in the Pilot Phase of the French E-Invoicing. This way you are able to test it before it becomes mandatory.",
    )
    l10n_fr_pdp_send_to_ppf = fields.Boolean(
        related='company_id.l10n_fr_pdp_send_to_ppf', readonly=False,
        string="Send to PPF",
        help="Activate Flux 1 regulatory data, Flux 6 mandatory statuses and Flux 10 e-reporting generation for this company.",
    )
    l10n_fr_pdp_annuaire_start_date = fields.Date(
        related='company_id.l10n_fr_pdp_annuaire_start_date',
        string="Annuaire Start Date",
        help="The date on which the company is registered on the annuaire for the French e-invoicing.",
    )
    l10n_fr_pdp_registered = fields.Boolean(
        related='company_id.l10n_fr_pdp_registered',
        string="Approved Platform Registered",
    )
    l10n_fr_pdp_periodicity = fields.Selection(
        string="Flow 10 Report Periodicity",
        related='company_id.l10n_fr_pdp_periodicity', readonly=False,
        required=True,
        help="""Legal reporting period for transaction and payments flows according to the TVA regime table.
        Real Monthly Normal Regime : transactions reported by decade, payments reported monthly
        Real Normal Quarterly Regime : transactions reported monthly, payments reported monthly
        Simplified VAT Regime (Monthly) : transactions reported monthly, payments reported monthly
        Franchised VAT Regime (Bimonthly) : transactions reported bimonthly, payments reported bimonthly
        """,
    )

    def action_open_pdp_form(self):
        registration_wizard = self.env['pdp.registration'].create({'company_id': self.company_id.id})
        return registration_wizard._action_open_pdp_form(reopen=False)

    def action_open_peppol_form(self):
        self.ensure_one()
        if self.country_code != 'FR' and self.account_peppol_eas != '0225':
            return super().action_open_peppol_form()
        return self.action_open_pdp_form()

    @api.depends('company_id.l10n_fr_pdp_pilot_phase')
    def _compute_l10n_fr_pdp_pilot_phase(self):
        for record in self:
            record.l10n_fr_pdp_pilot_phase = record.company_id.l10n_fr_pdp_pilot_phase

    def _inverse_l10n_fr_pdp_pilot_phase(self):
        pass

    # TODO: remove in master
    @api.model
    def _pdp_ensure_selection_value(self, model_name, field_name, new_value):
        # hack to load new selection values in stable
        field = self.env[model_name]._fields[field_name]
        if new_value not in {value for value, name in field.get_description(self.env)['selection']}:
            self.env['ir.model.fields'].invalidate_model(['selection_ids'])
            self.env['ir.model.fields.selection'].sudo()._update_selection(model_name, field_name, field.selection)
            self.env.registry.clear_cache()
