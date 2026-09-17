# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ph_qrph_transaction_ids = fields.Many2many(
        comodel_name='l10n_ph.qrph.transaction',
        string="QRPH Codes",
        groups='account.group_account_invoice',
        copy=False,
    )

    def _get_name_invoice_report(self):
        self.ensure_one()
        if (
            self.move_type == 'out_invoice'
            and self.company_id.account_fiscal_country_id.code == 'PH'
            and all(self._l10n_ph_cas_get_tax_groups().values())
        ):
            return 'l10n_ph.report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_ph_cas_get_tax_groups(self):
        """ Return the ids of the tax groups the BIR CAS invoice needs."""
        self.ensure_one()
        chart_template = self.env['account.chart.template'].with_company(self.company_id)
        return {
            key: (chart_template.ref(xmlid, raise_if_not_found=False) or self.env['account.tax.group']).id
            for key, xmlid in {
                'vatable': 'l10n_ph_tax_group_vatable',
                'zero_rated': 'l10n_ph_tax_group_zero_rated',
                'vat_exempt': 'l10n_ph_tax_group_vat_exempt',
                'percentage_tax': 'l10n_ph_tax_group_percentage_tax',
            }.items()
        }

    def _l10n_ph_cas_get_invoice_report_values(self):
        """ Compute the BIR CAS invoice category and amount breakdowns used by the l10n_ph CAS invoice report. """
        self.ensure_one()
        group_ids = self._l10n_ph_cas_get_tax_groups()
        vals = {
            'vatable_base': 0.0,
            'vatable_tax': 0.0,
            'zero_rated_base': 0.0,
            'vat_exempt_base': 0.0,
            'percentage_tax_base': 0.0,
            'withholding_tax': self.withholding_total_amount_currency,
        }
        present_groups = set()

        for subtotal in (self.tax_totals or {}).get('subtotals', []):
            for tax_group in subtotal.get('tax_groups', []):
                base_amount = tax_group['display_base_amount_currency']
                if base_amount is False:
                    base_amount = tax_group['base_amount_currency']
                if tax_group['id'] == group_ids['vatable']:
                    present_groups.add('vatable')
                    vals['vatable_base'] += base_amount
                    vals['vatable_tax'] += tax_group['tax_amount_currency']
                elif tax_group['id'] == group_ids['zero_rated']:
                    present_groups.add('zero_rated')
                    vals['zero_rated_base'] += base_amount
                elif tax_group['id'] == group_ids['vat_exempt']:
                    present_groups.add('vat_exempt')
                    vals['vat_exempt_base'] += base_amount
                elif tax_group['id'] == group_ids['percentage_tax']:
                    vals['percentage_tax_base'] += base_amount

        if not self.company_id.l10n_ph_is_vat_registered:
            category = 'non_vat'
        elif present_groups and present_groups <= {'vat_exempt'}:
            category = 'vat_exempt'
        elif present_groups and present_groups <= {'zero_rated'}:
            category = 'zero_rated'
        else:
            category = 'mixed'
        vals['category'] = category
        vals['has_vat'] = 'vatable' in present_groups

        return vals

    def _generate_qr_code(self, silent_errors=False):
        # EXTENDS account
        # Tell the bank account which record it is minting a QRPH code for, so that the payment it
        # opens on Maya can be tied back to this invoice when checking whether it was paid.
        return super(
            AccountMove,
            self.with_context(l10n_ph_qrph_model='account.move', l10n_ph_qrph_model_id=str(self.id)),
        )._generate_qr_code(silent_errors)

    def _l10n_ph_qrph_cron_update_payment_status(self):
        """ Register the payment of every invoice whose QRPH code was paid since the last run.

        A code is minted for what is left to pay, so an invoice already partly paid is looked at too.
        """
        invoices = self.search([
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('l10n_ph_qrph_transaction_ids', '!=', False),
        ])
        return invoices._l10n_ph_qrph_update_payment_status()

    def action_l10n_ph_qrph_update_payment_status(self):
        """ Check with Maya whether the QRPH codes of these invoices were paid, without waiting for the cron. """
        invoices = self.filtered_domain([
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('l10n_ph_qrph_transaction_ids', '!=', False),
        ])
        return invoices._l10n_ph_qrph_update_payment_status()

    def _l10n_ph_qrph_update_payment_status(self):
        """ Register a payment on the invoices of self whose QRPH code Maya reports as paid. """
        paid_invoices = self.env['account.move']
        settled_transactions = self.env['l10n_ph.qrph.transaction']
        bodies = {}
        for invoice in self:
            if transaction := invoice.l10n_ph_qrph_transaction_ids._get_paid_transaction():
                paid_invoices |= invoice
                settled_transactions |= transaction
                bodies[invoice.id] = self.env._(
                    "Paid with QRPH, Maya payment %(payment)s.",
                    payment=transaction.maya_payment_id,
                )

        if not paid_invoices:
            return None

        paid_invoices._message_log_batch(bodies=bodies)
        payments = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=paid_invoices.ids,
        ).create({'group_payment': False}).action_create_payments()
        # A code pays an invoice once. Maya repeating its notification, or the invoice going back
        # to unpaid because its payment was undone, must not have the same code pay a second time.
        settled_transactions.settled_date = fields.Datetime.now()
        return payments
