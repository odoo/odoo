# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, fields


class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    def _get_invoice_matching_so_candidates(self, st_line, partner):
        """ Find a match between the bank transaction and some sale orders. If none of them are invoiced, there are
        returned to display a message to the user allowing him to show the matched sale orders.
        If some of them are already matched, the journal items are suggested to the user.

        :param st_line: A statement line.
        :param partner: The partner to consider.
        :return:
            {'allow_auto_reconcile': <bool>, 'amls': <account.move.line>} if some sale orders are invoiced.
            {'sale_orders': <sale.order>} otherwise.
        """
        assert self.rule_type == 'invoice_matching'
        for model in ('sale.order', 'sale.order.line', 'account.move', 'account.move.line'):
            self.env[model].flush_model()

        _numerical_tokens, exact_tokens, text_tokens = self._get_invoice_matching_st_line_tokens(st_line)
        if not (exact_tokens or text_tokens):
            return

        # Find the sale orders that are not yet invoiced or already invoices.
        domain = [
            ('company_id', '=', st_line.company_id.id),
            '|',
            ('invoice_status', 'in', ('to invoice', 'invoiced')),
            ('state', '=', 'sent'),
            '|',
            ('name', 'in', exact_tokens),
            ('name', 'in', text_tokens),
        ]
        sale_orders = self.env['sale.order'].search(domain)
        if sale_orders:
            results = {'sale_orders': sale_orders}

            # Find some related invoices.
            aml_domain = self._get_invoice_matching_amls_domain(st_line, partner)
            invoices = sale_orders.invoice_ids
            if not invoices:
                # The sale orders are not yet invoiced. Return them to allow the user to invoice them from
                # the bank reco widget.
                return results

            invoice_amls = invoices.line_ids.filtered_domain(aml_domain)

            matched_payments = invoices._get_reconciled_payments()
            payments_amls = matched_payments.line_ids.filtered_domain(aml_domain)

            amls = payments_amls | invoice_amls
            if not amls:
                # The invoices and their payments are all already reconciled. Don't match anything and let the others rules trying
                # to match potential payments instead.
                return

            results['amls'] = amls
            results['allow_auto_reconcile'] = True

            return results

    def _get_invoice_matching_rules_map(self):
        # EXTENDS account
        res = super()._get_invoice_matching_rules_map()
        res[0].append(self._get_invoice_matching_so_candidates)
        return res
