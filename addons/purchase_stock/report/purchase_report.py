# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.osv.expression import expression


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    picking_type_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    avg_receipt_delay = fields.Float(
        'Average Receipt Delay', digits=(16, 2), readonly=True, store=False,  # needs store=False to prevent showing up as a 'measure' option
        help="Amount of time between expected and effective receipt date. Due to a hack needed to calculate this, \
              every record will show the same average value, therefore only use this as an aggregated value with group_operator=avg")
    effective_date = fields.Datetime(string="Effective Date")

    def _select(self):
        return super(PurchaseReport, self)._select() + ", spt.warehouse_id as picking_type_id, po.effective_date as effective_date"

    def _from(self):
        return super(PurchaseReport, self)._from() + " left join stock_picking_type spt on (spt.id=po.picking_type_id)"

    def _group_by(self):
        return super(PurchaseReport, self)._group_by() + ", spt.warehouse_id, effective_date"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ This is a hack to allow us to correctly calculate the average of PO specific date values since
            the normal report query result will duplicate PO values across its PO lines during joins and
            lead to incorrect aggregation values.

            Only the AVG operator is supported for avg_receipt_delay.
        """
        avg_receipt_delay = next((field for field in fields if re.search(r'\bavg_receipt_delay\b', field)), False)

        if avg_receipt_delay:
            fields.remove(avg_receipt_delay)
            if any(field.split(':')[1].split('(')[0] != 'avg' for field in [avg_receipt_delay] if field):
                raise UserError("Value: 'avg_receipt_delay' should only be used to show an average. If you are seeing this message then it is being accessed incorrectly.")

        res = []
        if fields:
            res = super(PurchaseReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        if not res and avg_receipt_delay:
            res = [{}]

        if avg_receipt_delay:
            query = """ SELECT AVG(receipt_delay.po_receipt_delay)::decimal(16,2) AS avg_receipt_delay
                          FROM (
                              SELECT extract(epoch from age(po.effective_date, po.date_planned))/(24*60*60) AS po_receipt_delay
                              FROM purchase_order po
                              WHERE po.id IN (
                                  SELECT "purchase_report"."order_id" FROM %s WHERE %s)
                              ) AS receipt_delay
                    """

            subdomain = domain + [('company_id', '=', self.env.company.id), ('effective_date', '!=', False)]
            subtables, subwhere, subparams = expression(subdomain, self).query.get_sql()

            self.env.cr.execute(query % (subtables, subwhere), subparams)
            res[0].update({
                '__count': 1,
                avg_receipt_delay.split(':')[0]: self.env.cr.fetchall()[0][0],
            })
        return res
