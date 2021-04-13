# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = ['account.move', 'edi']

    edi_document_ids = fields.One2many(
        comodel_name='edi.document',
        inverse_name='move_id')

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    ####################################################
    # Export Electronic Document
    ####################################################

    def _prepare_edi_vals_to_export(self):
        ''' The purpose of this helper is the same as '_prepare_edi_vals_to_export' but for a single invoice line.
        This includes the computation of the tax details for each invoice line or the management of the discount.
        Indeed, in some EDI, we need to provide extra values depending the discount such as:
        - the discount as an amount instead of a percentage.
        - the price_unit but after subtraction of the discount.

        :return: A python dict containing default pre-processed values.
        '''
        self.ensure_one()

        def convert(amount):
            return self.currency_id._convert(amount, self.company_currency_id, self.company_id, self.date)

        res = {
            'line': self,
            'price_unit_after_discount': self.price_unit * (1 - (self.discount / 100.0)),
            'price_subtotal_before_discount': self.currency_id.round(self.price_unit * self.quantity),
            'price_subtotal_unit': self.currency_id.round(self.price_subtotal / self.quantity) if self.quantity else 0.0,
            'price_total_unit': self.currency_id.round(self.price_total / self.quantity) if self.quantity else 0.0,
        }

        res['price_discount'] = res['price_subtotal_before_discount'] - self.price_subtotal

        # Tax details.
        tax_detail_per_tax = {}
        taxes_res = self.tax_ids.compute_all(
            res['price_unit_after_discount'],
            currency=self.currency_id,
            quantity=self.quantity,
            product=self.product_id,
            partner=self.partner_id,
            is_refund=self.move_id.move_type in ('in_refund', 'out_refund'),
        )
        taxes_added_to_base = set()
        for tax_vals in taxes_res['taxes']:
            tax_rep = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
            tax = tax_rep.tax_id
            tax_detail_per_tax.setdefault(tax, {
                'tax': tax,
                'orig_tax': tax_vals['group'].id if tax_vals['group'] else tax.id,
                'tax_base_amount_currency': 0.0,
                'tax_amount_currency': 0.0,
                'tax_amount_currency_closing': 0.0,
                'tag_ids': set(),
            })
            vals = tax_detail_per_tax[tax]

            # Avoid adding multiple times the same base (e.g. with multiple repartition lines).
            if tax.id not in taxes_added_to_base:
                vals['tax_base_amount_currency'] = tax_vals['base']
                taxes_added_to_base.add(tax.id)

            vals['tax_amount_currency'] += tax_vals['amount']
            vals['tax_amount_currency_closing'] += tax_vals['amount'] if tax_rep.use_in_tax_closing else 0
            for tag_id in tax_rep.tag_ids:
                vals['tag_ids'].add(tag_id)

        res['tax_detail_vals_list'] = []
        for tax_detail_vals in tax_detail_per_tax.values():
            res['tax_detail_vals_list'].append({
                **tax_detail_vals,
                'tags': self.env['account.account.tag'].browse(tax_detail_vals['tag_ids']),
                'tax_base_amount': convert(tax_detail_vals['tax_base_amount_currency']),
                'tax_amount': convert(tax_detail_vals['tax_amount_currency']),
                'tax_amount_closing': convert(tax_detail_vals['tax_amount_currency_closing']),
            })

        return res

    def reconcile(self):
        # OVERRIDE
        # In some countries, the payments must be sent to the government under some condition. One of them could be
        # there is at least one reconciled invoice to the payment. Then, we need to update the state of the edi
        # documents during the reconciliation.
        all_lines = self + self.matched_debit_ids.debit_move_id + self.matched_credit_ids.credit_move_id
        payments = all_lines.move_id.filtered(lambda move: move.payment_id or move.statement_line_id)

        invoices_per_payment_before = {pay: pay._get_reconciled_invoices() for pay in payments}
        res = super().reconcile()
        invoices_per_payment_after = {pay: pay._get_reconciled_invoices() for pay in payments}

        changed_payments = self.env['account.move']
        for payment, invoices_after in invoices_per_payment_after.items():
            invoices_before = invoices_per_payment_before[payment]

            if set(invoices_after.ids) != set(invoices_before.ids):
                changed_payments |= payment
        changed_payments._update_payments_edi_documents()

        return res

    def remove_move_reconcile(self):
        # OVERRIDE
        # When a payment has been sent to the government, it usually contains some information about reconciled
        # invoices. If the user breaks a reconciliation, the related payments must be cancelled properly and then, a new
        # electronic document must be generated.
        all_lines = self + self.matched_debit_ids.debit_move_id + self.matched_credit_ids.credit_move_id
        payments = all_lines.move_id.filtered(lambda move: move.payment_id or move.statement_line_id)

        invoices_per_payment_before = {pay: pay._get_reconciled_invoices() for pay in payments}
        res = super().remove_move_reconcile()
        invoices_per_payment_after = {pay: pay._get_reconciled_invoices() for pay in payments}

        changed_payments = self.env['account.move']
        for payment, invoices_after in invoices_per_payment_after.items():
            invoices_before = invoices_per_payment_before[payment]

            if set(invoices_after.ids) != set(invoices_before.ids):
                changed_payments |= payment
        changed_payments._update_payments_edi_documents()

        return res
