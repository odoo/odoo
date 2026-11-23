from odoo import models, Command, api, _
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
                    'outbound_payment_method_line_ids': [
                        Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_out_third_party_checks').id}),
                    ],
                    'inbound_payment_method_line_ids': [
                        Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_new_third_party_checks').id}),
                        Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_in_third_party_checks').id}),
                    ],
                },
                "rejected_third_party_check": {
                    'name': _('Rejected Third Party Checks'),
                    'type': 'cash',
                    'outbound_payment_method_line_ids': [
                        Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_out_third_party_checks').id}),
                    ],
                    'inbound_payment_method_line_ids': [
                        Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_new_third_party_checks').id}),
                        Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_in_third_party_checks').id}),
                    ],
                },
            }
