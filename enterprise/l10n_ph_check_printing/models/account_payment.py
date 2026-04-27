# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.tools import formatLang


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends('payment_method_line_id', 'currency_id', 'amount', 'amount_company_currency_signed')
    def _compute_check_amount_in_words(self):
        """ Override to support the specific format for the cheques.
        As amounts are quite large, decimals are written as x/100.
        The currency isn't included in the text as it appears on the cheque layout.
        """
        ph_checks_payments = self.filtered(lambda p: p.company_id.account_check_printing_layout == 'l10n_ph_check_printing.action_print_check')
        for pay in ph_checks_payments:
            if pay.currency_id:
                # Start by getting the integer amount
                amount_company_currency = abs(pay.amount_company_currency_signed)
                check_amount = pay.currency_id.amount_to_text(int(amount_company_currency)).removesuffix(' Peso')
                if self.env.lang.startswith('en'):
                    check_amount = check_amount.replace('And ', '').replace(',', '')
                if amount_company_currency % 1 > 0:
                    # If there are decimals, we write them as x/100
                    check_amount += f' and {str(amount_company_currency).split(".")[1].ljust(2, "0")}/100'
                else:
                    check_amount += ' ONLY'
                pay.check_amount_in_words = check_amount
            else:
                pay.check_amount_in_words = False
        super(AccountPayment, self - ph_checks_payments)._compute_check_amount_in_words()

    @api.depends('payment_type', 'journal_id')
    def _compute_payment_method_line_id(self):
        # OVERRIDE account to be able to set checks by default in the new view.
        super()._compute_payment_method_line_id()
        if self.env.context.get('is_check_payment'):
            for record in self:
                method_line = record.journal_id.outbound_payment_method_line_ids.filtered(
                    lambda line: line.payment_method_id.code == 'check_printing'
                )
                if record.payment_type == 'outbound' and method_line:
                    record.payment_method_line_id = method_line[0]

    def _check_build_page_info(self, i, p):
        """ Override to add separate value for each part of the date, as well as remove the amount currency symbol """
        info = super()._check_build_page_info(i, p)
        info.update({
            'day': self.date.strftime('%d'),
            'month': self.date.strftime('%m'),
            'year': self.date.strftime('%Y'),
            'amount_no_currency': formatLang(self.env, abs(self.amount_company_currency_signed)) if i == 0 else 'VOID',
        })
        return info

    def _check_fill_line(self, amount_str):
        if self.company_id.account_check_printing_layout == 'l10n_ph_check_printing.action_print_check':
            return amount_str or ''
        return super()._check_fill_line(amount_str)
