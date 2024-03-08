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
    is_service = fields.Boolean("Is a Service", compute='_compute_is_service', store=True, compute_sudo=True)

    def _domain_sale_line_service(self, **kwargs):
        """
        Get the default generic services domain for sale.order.line.
        You can filter out domain leafs by passing kwargs of the form 'check_<leaf_field>=False'.
        Only 'is_service' cannot be disabled.

        :param kwargs: boolean kwargs of the form 'check_<leaf_field>=False'
        :return: a valid domain
        """
        return [
            ('is_service', '=', True),
            ('is_expense', '=', False) if kwargs.get("check_is_expense", True) else expression.TRUE_LEAF,
            ('is_downpayment', '=', False) if kwargs.get("check_is_downpayment", True) else expression.TRUE_LEAF,
            ('state', '=', 'sale') if kwargs.get("check_state", True) else expression.TRUE_LEAF,
        ]

    def _domain_sale_line_service_str(self, domain='', op='&', **kwargs):
        """
        Get the str version of the domain for services sale.order.line.
        Can be optionally aggregated with another domain for customization of the field domain definition

        :param str domain: static str representing the domain for the field definition. Assumed it's a valid domain
        :param str op: '&' or '|' depending on how the domain should be combined. Defaults to '&'
        :param kwargs: refer to :ref:`_domain_sale_line_service`
        :return: str version of the combined services sale.order.line domain.
        """
        if not domain:
            return str(self._domain_sale_line_service(**kwargs))
        if op not in ('&', '|'):
            raise ValueError(f"op is expected to be '&' or '|', got '{op}' instead.")
        domain = domain.replace('\r\n', '').replace('\n', '').strip()[1:-1].strip(", ")
        return f"['{op}', {domain}, {str(self._domain_sale_line_service(**kwargs))[1:-1]}]"

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

    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        # optimization for a SOL services name_search, to avoid joining on sale_order with too many lines
        if domain and ('is_service', '=', True) in domain and operator in ('like', 'ilike') and limit is not None:
            query = self.env['sale.order.line']._search(domain, limit=limit, order=None)
            query.order = f'{query.table}.order_id DESC, {query.table}.sequence, {query.table}.id'
            return query
        else:
            return super()._name_search(name, domain, operator, limit, order)
