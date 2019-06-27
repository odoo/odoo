# -*- coding: utf-8 -*-

from odoo import api, models


class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    def _get_sales_order(self, res):
        stl_ids = [l.get('st_line', {}).get('id') for l in res.get('lines', [])]
        if not stl_ids:
            return res
        # Search if we can find a sale order line that match the statement reference
        # DLE P88: `/home/dle/src/odoo/master-nochange-fp/addons/sale/tests/test_sale_order.py`
        # `test_reconciliation_with_so`
        self.env['sale.order'].flush(['invoice_status'])
        sql_query = """
            SELECT stl.id, array_agg(o.id) AS order_id
            FROM sale_order o,
                 account_bank_statement_line stl
            WHERE
                POSITION(lower(stl.name) IN lower(concat(o.name,o.reference))) != 0
              AND stl.id IN %s
              AND (stl.partner_id is null OR stl.partner_id = o.partner_id)
              AND (o.invoice_status = 'to invoice' OR o.state = 'sent')
              AND o.company_id = %s
            GROUP BY stl.id
            ORDER BY stl.id
        """
        company_id = res.get('lines')[0].get('st_line', {}).get('company_id')
        self.env.cr.execute(sql_query, (tuple(stl_ids), company_id))
        results = {}
        for el in self.env.cr.dictfetchall():
            results[el.get('id')] = el.get('order_id')
        for line in res.get('lines', []):
            so_ids = results.get(line['st_line'].get('id'))
            if so_ids:
                line['sale_order_ids'] = so_ids
        return res

    @api.model
    def get_bank_statement_line_data(self, st_line_ids, excluded_ids=None):
        res = super(AccountReconciliation, self).get_bank_statement_line_data(st_line_ids=st_line_ids, excluded_ids=excluded_ids)
        res = self._get_sales_order(res)
        return res
