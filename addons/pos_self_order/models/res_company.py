# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _load_pos_self_data_fields(self, config_id):
        return ['name', 'currency_id', 'tax_calculation_rounding_method', 'country_id', 'account_fiscal_country_id', 'vat',
         'phone', 'email', 'website', 'point_of_sale_use_ticket_qr_code', 'point_of_sale_ticket_portal_url_display_mode',
        ]
