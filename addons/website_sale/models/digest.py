# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DigestDigest(models.Model):
    _inherit = 'digest.digest'

    kpi_website_sale_total = fields.Boolean(string="eCommerce Sales")
    kpi_website_sale_total_value = fields.Monetary(compute='_compute_kpi_website_sale_total_value')

    def _compute_kpi_website_sale_total_value(self):
        self._raise_if_not_member_of('sales_team.group_sale_salesman_all_leads')
        self._calculate_kpi(
            'sale.report',
            'kpi_website_sale_total_value',
            date_field='date',
            additional_domain=[('state', 'not in', ['draft', 'cancel', 'sent']), ('website_id', '!=', False)],
            sum_field='price_subtotal',
        )

    def _get_kpi_custom_settings(self, company, user):
        res = super()._get_kpi_custom_settings(company, user)
        menu_id = self.env.ref('website.menu_website_configuration').id
        res['kpi_action']['kpi_website_sale_total'] = f'website.backend_dashboard?menu_id={menu_id}'
        res['kpi_sequence']['kpi_website_sale_total'] = 2505
        return res
