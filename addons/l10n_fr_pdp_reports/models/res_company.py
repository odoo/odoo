from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pdp_enabled = fields.Boolean(
        string="Enable PDP E-reporting",
        help="Activate Flux 10 e-reporting generation for this company.",
    )
    l10n_fr_pdp_route_code = fields.Char(
        string="PDP Routing Identifier",
        help="Temporary Annuaire routing identifier used in the Flux 10 headers until the real API is available.",
    )
    l10n_fr_pdp_periodicity = fields.Selection(
        selection=[
            ('decade', "Décade (1-10 / 11-20 / 21-fin)"),
            ('monthly', "Mensuelle"),
            ('bimonthly', "Bimestrielle"),
        ],
        string="Transaction Periodicity",
        default='decade',
        help="Legal reporting period for transaction flows according to the TVA regime table.",
    )
    l10n_fr_pdp_payment_periodicity = fields.Selection(
        selection=[('monthly', "Mensuelle"), ('bimonthly', "Bimestrielle")],
        string="Payment Periodicity",
        default='monthly',
        help="Frequency applied to payment flows; defaults to the monthly deadline described in Tableau 12.",
    )
    l10n_fr_pdp_tax_due_code = fields.Selection(
        selection=[('1', "Débits"), ('2', "Livraisons/Prestations"), ('3', "Encaissements")],
        string="Tax Due Date Type Code",
        default='3',
        help="TT-64 code used for tax due date type in Flux 10 (1=Débits, 2=Livraisons/Prestations, 3=Encaissements).",
    )
    l10n_fr_pdp_deadline_override_start = fields.Integer(
        string="Deadline Override Start Day",
        help="Optional start day (1-31) to simulate the opening of the send window for testing.",
    )
    l10n_fr_pdp_deadline_override_end = fields.Integer(
        string="Deadline Override End Day",
        help="Optional end day (1-31) to simulate the closing of the send window for testing.",
    )
    l10n_fr_pdp_send_mode = fields.Selection(
        selection=[('auto', "Automatic cron"), ('manual', "Manual only")],
        string="PDP Send Mode",
        default='auto',
        help="Choose whether the sending cron dispatches ready flows automatically.",
    )

    def _l10n_fr_pdp_ensure_journal(self):
        """Create the e-reporting journal for each FR company with PDP enabled."""
        Journal = self.env['account.journal']

        for company in self:
            if company.country_code != 'FR' or not company.l10n_fr_pdp_enabled:
                continue

            existing = Journal.search([
                ('company_id', '=', company.id),
                ('code', '=', 'EREP'),
            ], limit=1)
            if existing:
                continue

            Journal.with_company(company.id).create({
                'name': 'E-Reporting',
                'code': 'EREP',
                'type': 'sale',
                'show_on_dashboard': True,
                'company_id': company.id,
            })

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            if company.country_code == 'FR' and company.l10n_fr_pdp_enabled:
                company._l10n_fr_pdp_ensure_journal()
        return companies

    def write(self, vals):
        res = super().write(vals)

        if 'l10n_fr_pdp_enabled' in vals:
            enabled = self.filtered(lambda c: c.l10n_fr_pdp_enabled and c.country_code == 'FR')
            enabled._l10n_fr_pdp_ensure_journal()

        return res
