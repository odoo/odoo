import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.tools import float_compare

from odoo.addons.iap.tools import iap_tools
from odoo.addons.l10n_fr_pdp.utils import drom_com_territories


_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pdp_late_payment_penalties_rate = fields.Float(
        string="Late Payment Penalties Rate",
        default=10.0,
        digits=(16, 2),
        help="Calculated as the ECB MRO rate + 10 points. If manually edited, it won't be recomputed automatically, you'll need to update it yourself.",
    )
    l10n_fr_pdp_late_payment_penalties_automatic = fields.Boolean(
        string="Update Late Payment Penalties Automatically",
        default=True,
    )
    l10n_fr_pdp_late_payment_penalties_period = fields.Date(
        string="Rate Applicable Since",
        readonly=True,
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

    def write(self, vals):
        if not {
            'l10n_fr_pdp_late_payment_penalties_rate',
            'l10n_fr_pdp_late_payment_penalties_automatic',
        } & vals.keys():
            return super().write(vals)

        automatic_update = self.env.context.get('l10n_fr_pdp_automatic_rate_update')
        for company in self:
            company_vals = dict(vals)
            if not automatic_update:
                if (
                    'l10n_fr_pdp_late_payment_penalties_rate' in vals
                    and float_compare(
                        company.l10n_fr_pdp_late_payment_penalties_rate,
                        vals['l10n_fr_pdp_late_payment_penalties_rate'],
                        precision_digits=2,
                    )
                ):
                    company_vals.update({
                        'l10n_fr_pdp_late_payment_penalties_automatic': False,
                        'l10n_fr_pdp_late_payment_penalties_period': False,
                    })
                elif (
                    'l10n_fr_pdp_late_payment_penalties_automatic' in vals
                    and company.l10n_fr_pdp_late_payment_penalties_automatic != vals['l10n_fr_pdp_late_payment_penalties_automatic']
                ):
                    company_vals['l10n_fr_pdp_late_payment_penalties_period'] = False
            super(ResCompany, company).write(company_vals)
        return True

    @api.model
    def _l10n_fr_pdp_get_semester_start(self, reference_date=None):
        reference_date = fields.Date.to_date(reference_date or fields.Date.today())
        return reference_date.replace(
            month=1 if reference_date.month <= 6 else 7,
            day=1,
        )

    def _l10n_fr_pdp_fetch_late_payment_penalties_rates(self, period_starts):
        self.ensure_one()
        edi_mode = self._get_peppol_edi_mode()
        server_url = self.env['account_edi_proxy_client.user']._get_server_url(
            proxy_type='pdp',
            edi_mode=edi_mode,
        )
        try:
            response = iap_tools.iap_jsonrpc(
                f'{server_url}/api/pdp/1/late_payment_penalty_rates',
                params={
                    'period_starts': [fields.Date.to_string(period_start) for period_start in period_starts],
                },
            )
            rates_by_period = self._l10n_fr_pdp_parse_late_payment_penalties_rates_response(
                response,
                period_starts,
            )
        except (AccessError, KeyError, TypeError, ValueError) as error:
            _logger.warning(
                "Unable to update the late payment penalty rates from IAP: %s",
                error,
            )
            return {}
        return rates_by_period

    def _l10n_fr_pdp_parse_late_payment_penalties_rates_response(self, response, period_starts):
        rates_by_period = {
            fields.Date.to_date(values['period_start']): float(values['late_payment_penalty_rate'])
            for values in response
        }
        if rates_by_period.keys() != set(period_starts):
            raise ValueError("The IAP response does not match the requested periods.")
        return rates_by_period

    def _l10n_fr_pdp_set_automatic_late_payment_penalties_rate(self, rate, period_start):
        self.ensure_one()
        self.sudo().with_context(
            l10n_fr_pdp_automatic_rate_update=True,
        ).write({
            'l10n_fr_pdp_late_payment_penalties_rate': rate,
            'l10n_fr_pdp_late_payment_penalties_automatic': True,
            'l10n_fr_pdp_late_payment_penalties_period': period_start,
        })

    def _l10n_fr_pdp_get_late_payment_penalties_rate(self, period_start, rates_by_period):
        self.ensure_one()
        if not self.l10n_fr_pdp_late_payment_penalties_automatic or self._get_peppol_edi_mode() == 'demo':
            return self.l10n_fr_pdp_late_payment_penalties_rate
        if self.l10n_fr_pdp_late_payment_penalties_period == period_start:
            return self.l10n_fr_pdp_late_payment_penalties_rate

        rate = rates_by_period.get(period_start)
        if rate is None:
            return False
        if period_start == self._l10n_fr_pdp_get_semester_start():
            self._l10n_fr_pdp_set_automatic_late_payment_penalties_rate(
                rate,
                period_start,
            )
        return rate
