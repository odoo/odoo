# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.osv.expression import expression


class StockReport(models.Model):
    _inherit = 'stock.report'

    valuation = fields.Float("Valuation of Inventory using a Domain", readonly=True, store=False,
                             help="Note that you can only access this value in the read_group, only the sum operator is supported")
    stock_value = fields.Float("Total Valuation of Inventory", readonly=True, store=False,
                               help="Note that you can only access this value in the read_group, only the sum operator is supported and only date_done is used from the domain")

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """
            This is a hack made in order to improve performance as adding
            inventory valuation on the report itself would be too costly.

            Basically when asked to return the valuation, it will run a smaller
            SQL query that will calculate the inventory valuation on the given
            domain.

            Only the SUM operator is supported for valuation.

            We can also get the stock_value of the inventory at a specific date
            (default is today).

            The same applies to this stock_value field, it only supports the sum operator
            and does not support the group by.

            NB: This should probably be implemented in a read instead of read_group since
                we don't support grouping

            NB: We might be able to avoid doing this hack by optimizing the query used to
                generate the report (= TODO: see nse)
        """
        stock_value = next((field for field in fields if re.search(r'\bstock_value\b', field)), False)
        valuation = next((field for field in fields if re.search(r'\bvaluation\b', field)), False)

        if stock_value:
            fields.remove(stock_value)

        if valuation:
            fields.remove(valuation)

        if stock_value or valuation:
            if groupby:
                raise UserError("valuation and stock_value don't support grouping")

            if any(field.split(':')[1].split('(')[0] != 'sum' for field in [stock_value, valuation] if field):
                raise UserError("read_group only support operator sum for valuation and stock_value")

        res = []
        if fields:
            res = super(StockReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        if not res and (stock_value or valuation):
            res = [{}]

        if stock_value:
            products = self.env['product.product'].with_context(active_test=False)
            # Split the recordset for faster computing.
            value = sum(
                product.value_svl
                for products_split in self.env.cr.split_for_in_conditions(
                    products.search([("product_tmpl_id.type", "=", "product")]).ids
                )
                for product in products.browse(products_split)
            )

            res[0].update({
                '__count': 1,
                stock_value.split(':')[0]: value,
            })

        if valuation:
            query = """
                SELECT
                    SUM(move_valuation.valuation) as valuation
                FROM (
                    SELECT
                        sum(svl.value) AS valuation
                    FROM
                        stock_move move
                        INNER JOIN stock_valuation_layer AS svl ON svl.stock_move_id = move.id
                    WHERE
                        move.id IN (
                            SELECT "stock_report".id FROM %s WHERE %s)
                 GROUP BY
                        move.id
                ) as move_valuation
            """

            subdomain = domain + [('company_id', '=', self.env.company.id)]
            subtables, subwhere, subparams = expression(subdomain, self).query.get_sql()

            self.env.cr.execute(query % (subtables, subwhere), subparams)
            res[0].update({
                '__count': 1,
                valuation.split(':')[0]: self.env.cr.fetchall()[0][0],
            })

        return res
