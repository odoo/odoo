# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _l10n_us_check_printing_generate_micr_line(self):
        """ Generate MICR line to be printed on US blank checks.
        A - ⑆ (transit: used to delimit a bank code),
        B - ⑇ (amount: used to delimit a transaction amount),
        C - ⑈ (on - us: used to delimit a customer account number),
        D - ⑉ (dash: used to delimit parts of numbers—e.g., routing numbers or account numbers). """
        micr_check_number = self.check_number or '000000'
        micr_bank_routing = self.journal_id.bank_account_id.aba_routing or '000000000'
        micr_bank_acc_number = self.journal_id.bank_acc_number or '000000000'
        return f"C{micr_check_number}C   A{micr_bank_routing}A   {micr_bank_acc_number}C"

    def _check_build_page_info(self, i, p):
        # EXTENDS 'account_check_printing'
        page = super()._check_build_page_info(i, p)
        bank = self.journal_id.bank_id

        page.update({
            'company_street': ' '.join(street for street in (self.company_id.street, self.company_id.street2) if street),
            'company_city_state': ' '.join(c for c in (self.company_id.city, self.company_id.state_id.code, self.company_id.country_code, self.company_id.zip) if c),
            'company_name': self.company_id.name,
            'company_logo': self.company_id.logo,
            'bank_name': bank.name,
            'bank_street': ' '.join(bank_street for bank_street in (bank.street, bank.street2) if bank_street),
            'bank_city_state': ' '.join(bank_data for bank_data in (bank.city, bank.state.code, bank.zip) if bank_data),
            'bank_routing': self.journal_id.bank_account_id.aba_routing,
            'partner_street': ' '.join(street for street in (self.partner_id.street, self.partner_id.street2) if street),
            'partner_city_state': ' '.join(c for c in (self.partner_id.city, self.partner_id.state_id.code, self.partner_id.country_code, self.partner_id.zip) if c),
            'ckus_amount_in_word': self.check_amount_in_words + '*****',
            'ckus_special_line': self._l10n_us_check_printing_generate_micr_line(),
        })

        return page
