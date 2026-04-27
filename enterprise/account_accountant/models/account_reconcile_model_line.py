from odoo import models, Command, _
from odoo.exceptions import UserError

import re

from math import copysign


class AccountReconcileModelLine(models.Model):
    _inherit = 'account.reconcile.model.line'

    def _prepare_aml_vals(self, partner):
        """ Prepare a dictionary that will be used later to create a new journal item (account.move.line) for the
        given reconcile model line.

        :param partner: The partner to be linked to the journal item.
        :return:        A python dictionary.
        """
        self.ensure_one()

        taxes = self.tax_ids
        if taxes and partner:
            fiscal_position = self.env['account.fiscal.position']._get_fiscal_position(partner)
            if fiscal_position:
                taxes = fiscal_position.map_tax(taxes)

        values = {
            'name': self.label,
            'partner_id': partner.id,
            'analytic_distribution': self.analytic_distribution,
            'tax_ids': [Command.set(taxes.ids)],
            'reconcile_model_id': self.model_id.id,
        }
        if self.account_id:
            values['account_id'] = self.account_id.id
        return values

    def _apply_in_manual_widget(self, residual_amount_currency, partner, currency):
        """ Prepare a dictionary that will be used later to create a new journal item (account.move.line) for the
        given reconcile model line used by the manual reconciliation widget.

        Note: 'journal_id' is added to the returned dictionary even if it is a related readonly field.
        It's a hack for the manual reconciliation widget. Indeed, a single journal entry will be created for each
        journal.

        :param residual_amount_currency:    The current balance expressed in the account's currency.
        :param partner:                     The partner to be linked to the journal item.
        :param currency:                    The currency set on the account in the manual reconciliation widget.
        :return:                            A python dictionary.
        """
        self.ensure_one()

        if self.amount_type == 'percentage':
            amount_currency = currency.round(residual_amount_currency * (self.amount / 100.0))
        elif self.amount_type == 'fixed':
            sign = 1 if residual_amount_currency > 0.0 else -1
            amount_currency = currency.round(self.amount * sign)
        else:
            raise UserError(_("This reconciliation model can't be used in the manual reconciliation widget because its "
                              "configuration is not adapted"))

        return {
            **self._prepare_aml_vals(partner),
            'currency_id': currency.id,
            'amount_currency': amount_currency,
            'journal_id': self.journal_id.id,
        }

    def _apply_in_bank_widget(self, residual_amount_currency, partner, st_line):
        """ Prepare a dictionary that will be used later to create a new journal item (account.move.line) for the
        given reconcile model line used by the bank reconciliation widget.

        :param residual_amount_currency:    The current balance expressed in the statement line's currency.
        :param partner:                     The partner to be linked to the journal item.
        :param st_line:                     The statement line mounted inside the bank reconciliation widget.
        :return:                            A python dictionary.
        """
        self.ensure_one()
        currency = st_line.foreign_currency_id or st_line.journal_id.currency_id or st_line.company_currency_id

        aml_values = {'currency_id': currency.id}

        if self.amount_type == 'percentage_st_line':
            transaction_amount, transaction_currency, journal_amount, journal_currency, _company_amount, _company_currency \
                = st_line._get_accounting_amounts_and_currencies()
            if self.model_id.rule_type == 'writeoff_button' and self.model_id.counterpart_type in ('sale', 'purchase'):
                # The invoice should be created using the transaction currency.
                aml_values['amount_currency'] = currency.round(-transaction_amount * self.amount / 100.0)
                aml_values['percentage_st_line'] = self.amount / 100.0
                aml_values['currency_id'] = transaction_currency.id
            else:
                # The additional journal items follow the journal currency.
                aml_values['amount_currency'] = currency.round(-journal_amount * self.amount / 100.0)
                aml_values['currency_id'] = journal_currency.id
        elif self.amount_type == 'regex':
            match = re.search(self.amount_string, st_line.payment_ref)
            if match:
                sign = 1 if residual_amount_currency > 0.0 else -1
                decimal_separator = self.model_id.decimal_separator
                try:
                    extracted_match_group = re.sub(r'[^\d' + decimal_separator + ']', '', match.group(1))
                    extracted_balance = float(extracted_match_group.replace(decimal_separator, '.'))
                    aml_values['amount_currency'] = copysign(extracted_balance * sign, residual_amount_currency)
                except ValueError:
                    aml_values['amount_currency'] = 0.0
            else:
                aml_values['amount_currency'] = 0.0

        if 'amount_currency' not in aml_values:
            aml_values.update(self._apply_in_manual_widget(residual_amount_currency, partner, currency))
        else:
            aml_values.update(self._prepare_aml_vals(partner))

        if not aml_values.get('name', False):
            aml_values['name'] = st_line.payment_ref

        return aml_values
