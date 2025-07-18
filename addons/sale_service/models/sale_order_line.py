# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import format_amount
from odoo.tools.sql import column_exists, create_column, create_index


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # used to know if generate a task and/or a project, depending on the product settings
    is_service = fields.Boolean("Is a Service", compute='_compute_is_service', store=True, compute_sudo=True, export_string_translation=False)

    def _domain_sale_line_service(self, **kwargs):
        """
        Get the default generic services domain for sale.order.line.
        You can filter out domain leafs by passing kwargs of the form 'check_<leaf_field>=False'.
        Only 'is_service' cannot be disabled.

        :param kwargs: boolean kwargs of the form 'check_<leaf_field>=False'
        :return: a valid domain
        """
        domain = [('is_service', '=', True)]
        if kwargs.get("check_is_expense", True):
            domain.append(('is_expense', '=', False))
        if kwargs.get("check_state", True):
            domain.append(('state', '=', 'sale'))
        return domain

    @api.depends('product_id.type')
    def _compute_is_service(self):
        self.fetch(['is_service', 'product_id'])
        self.product_id.fetch(['type'])
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

    def init(self):
        res = super().init()
        query_domain_sale_line = expression.expression([('is_service', '=', True)], self).query
        create_index(self._cr, 'sale_order_line_name_search_services_index',
                     self._table, ('order_id DESC', 'sequence', 'id'),
                     where=query_domain_sale_line.where_clause)
        return res

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

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        domain = args or []
        # optimization for a SOL services name_search, to avoid joining on sale_order with too many lines
        if domain and ('is_service', '=', True) in domain and operator in ('like', 'ilike') and limit is not None:
            sols = self.search_fetch(
                domain, ['display_name'], limit=limit, order='order_id.id DESC, sequence, id',
            )
            return [(sol.id, sol.display_name) for sol in sols]
        return super().name_search(name, domain, operator, limit)
