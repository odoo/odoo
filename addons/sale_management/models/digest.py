# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DigestDigest(models.Model):
    _inherit = 'digest.digest'

    kpi_all_sale_total = fields.Boolean('All Sales')
    kpi_all_sale_total_value = fields.Monetary(compute='_compute_kpi_sale_total_value')

    def _compute_kpi_sale_total_value(self):
        self._raise_if_not_member_of('sales_team.group_sale_salesman_all_leads')
        self._calculate_kpi(
            'sale.report',
            'kpi_all_sale_total_value',
            date_field='date',
            additional_domain=[('state', 'not in', ['draft', 'cancel', 'sent'])],
            sum_field='price_total',
        )

    def _get_kpi_custom_settings(self, company, user):
        res = super()._get_kpi_custom_settings(company, user)
        menu_id = self.env.ref('sale.sale_menu_root').id
        res['kpi_action']['kpi_all_sale_total'] = f'sale.report_all_channels_sales_action?menu_id={menu_id}'
        res['kpi_sequence']['kpi_all_sale_total'] = 2500
        return res
