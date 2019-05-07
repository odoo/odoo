# -*- coding: utf-8 -*-

from odoo import api, models


class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    def _get_sales_order(self, res):
        stl_ids = [l.get('st_line', {}).get('id') for l in res.get('lines', [])]
        if not stl_ids:
            return res
        # Search if we can find a sale order line that match the statement reference
        self.env['sale.order'].flush(['name', 'reference', 'invoice_status', 'company_id', 'state', 'partner_id'])
        self.env['account.bank.statement.line'].flush(['name', 'partner_id'])
        sql_query = """
            SELECT stl.id, array_agg(o.id) AS order_id, stl.partner_id, array_agg(o.partner_id) as order_partner
            FROM sale_order o,
                 account_bank_statement_line stl
            WHERE
                (POSITION(lower(o.name) IN lower(stl.name)) != 0
                OR POSITION(lower(o.reference) IN lower(stl.name)) != 0)
              AND stl.id IN %s
              AND (o.invoice_status = 'to invoice' OR o.state = 'sent')
              AND o.company_id = %s
            GROUP BY stl.id
            ORDER BY stl.id
        """
        company_id = res.get('lines')[0].get('st_line', {}).get('company_id')
        self.env.cr.execute(sql_query, (tuple(stl_ids), company_id))
        results = {}
        for el in self.env.cr.dictfetchall():
            results[el.get('id')] = (el.get('order_id'), el.get('partner_id'), el.get('order_partner'))
        for line in res.get('lines', []):
            so_data = results.get(line['st_line'].get('id'))
            if so_data:
                line['sale_order_ids'] = so_data[0]
                line['sale_order_prioritize'] = (not so_data[1]) or (so_data[1] in so_data[2])
        return res

    @api.model
    def get_bank_statement_line_data(self, st_line_ids, excluded_ids=None):
        res = super(AccountReconciliation, self).get_bank_statement_line_data(st_line_ids=st_line_ids, excluded_ids=excluded_ids)
        res = self._get_sales_order(res)
        return res
