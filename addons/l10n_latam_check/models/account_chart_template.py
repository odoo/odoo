from odoo import models, Command, api, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.model
    def _get_third_party_checks_country_codes(self):
        """ Return the list of country codes for the countries where third party checks journals should be created
        when installing the COA"""
        return ["AR"]

    def _create_bank_journals(self, company, acc_template_ref):
        res = super()._create_bank_journals(company, acc_template_ref)

        if company.country_id.code in self._get_third_party_checks_country_codes():
            self.env['account.journal'].create({
                'name': _('Third Party Checks'),
                'type': 'cash',
                'company_id': company.id,
                'outbound_payment_method_line_ids': [
                    Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_out_third_party_checks').id}),
                ],
                'inbound_payment_method_line_ids': [
                    Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_new_third_party_checks').id}),
                    Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_in_third_party_checks').id}),
                ]})
            self.env['account.journal'].create({
                'name': _('Rejected Third Party Checks'),
                'type': 'cash',
                'company_id': company.id,
                'outbound_payment_method_line_ids': [
                    Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_out_third_party_checks').id}),
                ],
                'inbound_payment_method_line_ids': [
                    Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_new_third_party_checks').id}),
                    Command.create({'payment_method_id': self.env.ref('l10n_latam_check.account_payment_method_in_third_party_checks').id}),
                ]})
        return res
