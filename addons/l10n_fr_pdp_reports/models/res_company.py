from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pdp_periodicity = fields.Selection(  # TODO prevent changing if flows exist ?
        selection=[
            ('normal_monthly', "Real Monthly Normal Regime"),
            ('normal_quarterly', "Real Normal Quarterly Regime"),
            ('simplified_monthly', "Simplified VAT Regime (Monthly)"),
            ('simplified_bimonthly', "Franchised VAT Regime (Bimonthly)"),
        ],
        string="Flow 10 Report Periodicity",
        default='normal_monthly',
        required=True,
        help="""Legal reporting period for transaction and payments flows according to the TVA regime table.
        Real Monthly Normal Regime : transactions reported by decade, payments reported monthly
        Real Normal Quarterly Regime : transactions reported monthly, payments reported monthly
        Simplified VAT Regime (Monthly) : transactions reported monthly, payments reported monthly
        Franchised VAT Regime (Bimonthly) : transactions reported bimonthly, payments reported bimonthly
        """,
    )
    l10n_fr_f10_enable_reporting = fields.Boolean(
        string="Enable Flux 10 Reporting",
        compute='_compute_l10n_fr_f10_enable_reporting',
        store=True,
        readonly=True,
    )
    l10n_fr_pdp_flow_10_start_date = fields.Date(compute='_compute_l10n_fr_pdp_flow_10_start_date')

    @api.depends('l10n_fr_pdp_annuaire_start_date', 'l10n_fr_pdp_periodicity')
    def _compute_l10n_fr_pdp_flow_10_start_date(self):
        for company in self:
            if company.l10n_fr_pdp_annuaire_start_date:
                period_data = self.env['l10n.fr.pdp.reports.flow']._get_period_flow_properties(
                    company,
                    company.l10n_fr_pdp_annuaire_start_date,
                    'payment',
                )
                company.l10n_fr_pdp_flow_10_start_date = period_data['period_start']
            else:
                company.l10n_fr_pdp_flow_10_start_date = None

    @api.depends('l10n_fr_pdp_send_to_ppf', 'account_fiscal_country_id', 'account_peppol_edi_user')
    def _compute_l10n_fr_f10_enable_reporting(self):
        for company in self:
            company.l10n_fr_f10_enable_reporting = (
                company.l10n_fr_pdp_send_to_ppf
                and company.l10n_fr_pdp_pilot_phase
                and company.account_peppol_edi_user
                and company.account_fiscal_country_id.code == 'FR'
                and company.currency_id == self.env.ref('base.EUR')
            )
