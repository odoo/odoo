from odoo import models, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _default_outbound_payment_methods(self):
        res = super()._default_outbound_payment_methods()
        if self.company_id.country_id.code != "AR":
            return res
        if self._is_payment_method_available('own_checks'):
            res |= self.env.ref('l10n_latam_check.account_payment_method_own_checks')
        if self._is_payment_method_available('return_third_party_checks'):
            res |= self.env.ref('l10n_latam_check.account_payment_method_return_third_party_checks')
        return res

    @api.model
    def _get_reusable_payment_methods(self):
        """ We are able to have multiple times Checks payment method in a journal """
        res = super()._get_reusable_payment_methods()
        res.add("own_checks")
        return res

    def create(self, vals_list):
        journals = super().create(vals_list)
        inbound_payment_accounts = self.env['account.account'].search([
            ('code', '=', '1.1.1.02.003'),
            ('company_ids', 'in', journals.company_id.ids)
        ]).grouped('company_ids')

        outbound_payment_accounts = self.env['account.account'].search([
            ('code', '=', '1.1.1.02.004'),
            ('company_ids', 'in', journals.company_id.ids)
        ]).grouped('company_ids')

        for journal in journals:
            if journal.country_code != 'AR' or journal.type not in ('bank', 'cash'):
                continue

            for payment_method_line in journal.inbound_payment_method_line_ids:
                if payment_method_line.payment_account_id:
                    continue
                payment_method_line.payment_account_id = inbound_payment_accounts.get(journal.company_id)

            for payment_method_line in journal.outbound_payment_method_line_ids:
                if payment_method_line.payment_account_id:
                    continue
                payment_method_line.payment_account_id = outbound_payment_accounts.get(journal.company_id)

        return journals
