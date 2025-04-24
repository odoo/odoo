from odoo import models, api, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @api.model
    def _get_third_party_checks_country_codes(self):
        """ Return the list of country codes for the countries where third party checks journals should be created
        when installing the COA"""
        return ["AR"]

    @template(model='account.journal')
    def _get_latam_check_account_journal(self, template_code):
        if self.env.company.country_id.code in self._get_third_party_checks_country_codes():
            return {
                "third_party_check": {
                    'name': _('Third Party Checks'),
                    'type': 'cash',
                    'outstanding_payment_account_id': 'base_outstanding_payments',
                },
                "rejected_third_party_check": {
                    'name': _('Rejected Third Party Checks'),
                    'type': 'cash',
                    'outstanding_payment_account_id': 'base_outstanding_payments',
                },
            }

    @template(model='account.account')
    def _get_latam_check_outstanding_account_account(self, template_code):
        if self.env.company.country_id.code in self._get_third_party_checks_country_codes():
            return {
                'base_outstanding_payments': {
                    'name': _("Outstanding Payments"),
                    'code': '1.1.1.02.004',
                    'reconcile': True,
                    'account_type': 'asset_current',
                },
            }

    @template(model='account.payment.method')
    def _get_latam_check_payment_methods(self, template_code):
        if self.env.company.country_id.code in self._get_third_party_checks_country_codes():
            return {
                "own_checks": {
                    'name': _('Own Checks'),
                    'code': 'own_checks',
                    'payment_type': 'outbound',
                },
                "new_third_party_checks": {
                    'name': _('New Third Party Checks'),
                    'code': 'new_third_party_checks',
                    'payment_type': 'inbound',
                },
                "in_third_party_checks": {
                    'name': _('Existing Third Party Checks'),
                    'code': 'in_third_party_checks',
                    'payment_type': 'inbound',
                },
                "out_third_party_checks": {
                    'name': _('Existing Third Party Checks'),
                    'code': 'out_third_party_checks',
                    'payment_type': 'outbound',
                },
                "return_third_party_checks": {
                    'name': _('Return Third Party Checks'),
                    'code': 'return_third_party_checks',
                    'payment_type': 'outbound',
                },
            }

    @template(model='account.journal')
    def _get_account_journal(self, template_code):
        journals = super()._get_account_journal(template_code)
        if self.env.company.country_id.code in self._get_third_party_checks_country_codes():
            journals['bank']['outstanding_payment_account_id'] = 'base_outstanding_payments'
        return journals
