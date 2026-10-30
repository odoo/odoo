from odoo import _, models
from odoo.fields import Domain
from odoo.tools import SQL

from odoo.addons.point_of_sale.report.pos_report_handler import report_section


class PosSalesDetailReport(models.AbstractModel):
    _inherit = 'pos.sales.detail.report'

    def _get_sections_columns(self):
        columns = super()._get_sections_columns()
        columns['global_discounts'] = [
            {
                'id': 'discount_count',
                'label': _('Count'),
                'type': 'integer',
                'align': 'right',
            },
            {
                'id': 'discount_amount',
                'label': _('Amount'),
                'type': 'monetary',
                'align': 'right',
            },
        ]
        return columns

    def _get_sale_lines_query(self, options, is_refund=None, extra_domain=None):
        query = super()._get_sale_lines_query(options, is_refund, extra_domain)

        line_table = query.table
        order_table = line_table._join('order_id')
        config_table = order_table._join('config_id')

        query.add_where(
            SQL(
                "(%s AND %s = %s) IS NOT TRUE",
                config_table['module_pos_discount'],
                line_table['product_id'],
                config_table['discount_product_id'],
            ),
        )

        return query

    def _is_discount_product(self, line):
        config = line.order_id.config_id
        return super()._is_discount_product(line) or (
            config.module_pos_discount and line.product_id == config.discount_product_id
        )

    @report_section(id='global_discounts', name='Global Discounts', sequence=42)
    def _section_global_discounts(self, options):
        domain = self._get_sale_line_domain(options) & Domain([('order_id.config_id.module_pos_discount', '=', True)])
        lines = self.env['pos.order.line'].search_fetch(domain,
            ['product_id', 'price_subtotal_incl', 'currency_id', 'company_id', 'order_id'],
        ).filtered(lambda line: (line.product_id == line.order_id.config_id.discount_product_id))

        discount_amount = sum(
            self._convert_to_report_currency(
                options,
                line.price_subtotal_incl, line.currency_id, line.company_id, line.order_id.date_order,
            )
            for line in lines
        )

        return {
            'name': _('Global Discounts'),
            'foldability': 'static',
            'discount_count': len(lines.order_id),
            'discount_amount': self._get_currency(options).round(abs(discount_amount)),
        }
