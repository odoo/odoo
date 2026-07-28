import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError

from odoo.addons.iap.tools import iap_tools


_logger = logging.getLogger(__name__)


class L10nFrPdpLatePaymentPenaltyRate(models.Model):
    _name = 'l10n_fr_pdp.late.payment.penalty.rate'
    _description = 'French PDP Late Payment Penalty Rate'

    period_start = fields.Date(required=True)
    rate = fields.Float(required=True, digits=(16, 2))

    _sql_constraints = [
        (
            'period_start_unique',
            'unique(period_start)',
            'A late payment penalty rate already exists for this period.',
        ),
    ]

    @api.model
    def _get_rates(self, company, period_starts):
        rates = self.sudo().search([('period_start', 'in', list(period_starts))])
        rates_by_period = {
            rate.period_start: rate.rate
            for rate in rates
        }
        missing_periods = sorted(set(period_starts) - rates_by_period.keys())
        if missing_periods:
            fetched_rates = self._fetch_rates(company, missing_periods)
            if fetched_rates:
                self.sudo().create([
                    {
                        'period_start': period_start,
                        'rate': rate,
                    }
                    for period_start, rate in fetched_rates.items()
                ])
                rates_by_period.update(fetched_rates)
        return rates_by_period

    @api.model
    def _fetch_rates(self, company, period_starts):
        company.ensure_one()
        edi_mode = company._get_peppol_edi_mode()
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
            rates_by_period = self._parse_rates_response(response, period_starts)
        except (AccessError, KeyError, TypeError, ValueError) as error:
            _logger.info(
                "Unable to update the late payment penalty rates from IAP: %s",
                error,
            )
            return {}
        return rates_by_period

    @api.model
    def _parse_rates_response(self, response, period_starts):
        rates_by_period = {
            fields.Date.to_date(values['period_start']): float(values['late_payment_penalty_rate'])
            for values in response
        }
        if rates_by_period.keys() != set(period_starts):
            raise ValueError("The IAP response does not match the requested periods.")
        return rates_by_period
