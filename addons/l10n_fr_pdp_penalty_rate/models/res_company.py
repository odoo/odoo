from odoo import api, fields, models

from odoo.addons.l10n_fr_pdp.utils import drom_com_territories


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pdp_manual_late_payment_penalties_rate = fields.Float(
        string="Late Payment Penalties Rate",
        default=10.0,
        digits=(16, 2),
    )
    l10n_fr_pdp_late_payment_penalties_automatic = fields.Boolean(
        string="Update Late Payment Penalties Automatically",
        default=True,
    )
    l10n_fr_pdp_late_payment_penalties_applicable = fields.Boolean(
        compute='_compute_l10n_fr_pdp_late_payment_penalties_applicable',
    )

    @api.depends('account_fiscal_country_id')
    def _compute_l10n_fr_pdp_late_payment_penalties_applicable(self):
        for company in self:
            territory_type = drom_com_territories.get_territory_type(company.account_fiscal_country_id.code)
            company.l10n_fr_pdp_late_payment_penalties_applicable = (
                territory_type in drom_com_territories.E_INVOICING_ZONES
            )

    @api.model
    def _l10n_fr_pdp_get_semester_start(self, reference_date=None):
        reference_date = fields.Date.to_date(reference_date or fields.Date.today())
        return reference_date.replace(
            month=1 if reference_date.month <= 6 else 7,
            day=1,
        )

    def _l10n_fr_pdp_get_late_payment_penalties_rates(self, period_starts):
        self.ensure_one()
        if not self.l10n_fr_pdp_late_payment_penalties_automatic or self._get_peppol_edi_mode() == 'demo':
            return dict.fromkeys(period_starts, self.l10n_fr_pdp_manual_late_payment_penalties_rate)

        return self.env['l10n_fr_pdp.late.payment.penalty.rate']._get_rates(self, period_starts)
