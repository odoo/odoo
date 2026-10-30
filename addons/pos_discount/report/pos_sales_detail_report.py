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

    def _get_sale_line_totals_query(self, is_refund=False, group_fields=[], extra_domain=None):
        query, select, group_by = super()._get_sale_line_totals_query(is_refund, group_fields, extra_domain)

        line_table = query.table
        order_table = line_table._join('order_id')
        config_table = order_table._join('config_id')

        query.add_where(
            SQL(
                "NOT (%s IS TRUE AND %s = %s)",
                config_table['module_pos_discount'],
                line_table['product_id'],
                config_table['discount_product_id'],
            ),
        )

        return query, select, group_by

    @report_section(id='global_discounts', name='Global Discounts', sequence=42)
    def _section_global_discounts(self):
        domain = self._get_sale_line_domain() & Domain([('order_id.config_id.module_pos_discount', '=', True)])
        lines = self.env['pos.order.line'].search_fetch(domain,
            ['product_id', 'price_subtotal_incl', 'currency_id', 'company_id', 'order_id'],
        ).filtered(lambda line: (line.product_id == line.order_id.config_id.discount_product_id))

        discount_amount = sum(
            self._convert_to_report_currency(
                line.price_subtotal_incl, line.currency_id, line.company_id, line.order_id.date_order,
            )
            for line in lines
        )

        return {
            'name': _('Global Discounts'),
            'foldability': 'static',
            'style': 'bold',
            'discount_count': len(lines.order_id),
            'discount_amount': self._get_currency().round(abs(discount_amount)),
        }
