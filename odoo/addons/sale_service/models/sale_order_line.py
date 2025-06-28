# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby

from odoo import api, fields, models
from odoo.tools import format_amount
from odoo.tools.sql import column_exists, create_column


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # used to know if generate a task and/or a project, depending on the product settings
    is_service = fields.Boolean("Is a Service", compute='_compute_is_service', store=True, compute_sudo=True)

    @api.depends('product_id.type')
    def _compute_is_service(self):
        for so_line in self:
            so_line.is_service = so_line.product_id.type == 'service'

    def _auto_init(self):
        """
        Create column to stop ORM from computing it himself (too slow)
        """
        if not column_exists(self.env.cr, 'sale_order_line', 'is_service'):
            create_column(self.env.cr, 'sale_order_line', 'is_service', 'bool')
            self.env.cr.execute("""
                UPDATE sale_order_line line
                SET is_service = (pt.type = 'service')
                FROM product_product pp
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE pp.id = line.product_id
            """)
        return super()._auto_init()

    def _additional_name_per_id(self):
        name_per_id = super()._additional_name_per_id() if not self.env.context.get('hide_partner_ref') else {}
        if not self.env.context.get('with_price_unit'):
            return name_per_id

        sols_list = [list(sols) for dummy, sols in groupby(self, lambda sol: (sol.order_id, sol.product_id))]
        for sols in sols_list:
            if len(sols) <= 1 or not all(sol.is_service for sol in sols):
                continue
            for line in sols:
                additional_name = name_per_id.get(line.id)
                name = format_amount(self.env, line.price_unit, line.currency_id)
                if additional_name:
                    name += f' {additional_name}'
                name_per_id[line.id] = f'- {name}'

        return name_per_id
