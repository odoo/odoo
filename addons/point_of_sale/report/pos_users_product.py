# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from odoo import api, models


class ReportPosUserProduct(models.AbstractModel):
    _name = 'report.point_of_sale.report_usersproduct'

    def _get_data(self, statements):
        res = dict(map(lambda x: (x, False), statements.ids))
        for statement in statements:
            order_ids = [line.pos_statement_id.id for line in statement.line_ids if line.pos_statement_id.state == 'paid']
            if len(order_ids):
                query = """
                    SELECT
                        SUM(qty) AS qty,
                        l.price_unit*SUM(l.qty) AS amt,
                        t.name AS name,
                        p.default_code AS code,
                        pu.name AS uom
                    FROM
                        product_product p,
                        product_template t,
                        product_uom pu,
                        pos_order_line l
                    WHERE
                        order_id IN %s AND
                        p.product_tmpl_id=t.id AND
                        l.product_id=p.id AND
                        pu.id=t.uom_id
                    GROUP BY t.name, p.default_code, pu.name, l.price_unit"""
                self.env.cr.execute(query, (tuple(order_ids),))
                res[statement.id] = self.env.cr.dictfetchall()
        return res

    def _get_user(self, statements):
        return ', '.join(set([statement.user_id.name for statement in statements]))

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name('point_of_sale.report_usersproduct')
        statements = self.env['account.bank.statement'].browse(self.ids)
        docargs = {
            'doc_ids': self.ids,
            'doc_model': report.model,
            'docs': statements,
            'time': time,
            'data': self._get_data(statements),
            'users': self._get_user(statements),
        }
        return Report.render('point_of_sale.report_usersproduct', docargs)
