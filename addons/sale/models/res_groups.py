# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResGroups(models.Model):
    _inherit = 'res.groups'

    def _get_light_group_xmlids(self):
        return super()._get_light_group_xmlids() + (
            'sale.group_discount_per_so_line',
            'sale.group_proforma_sales',
            'sale.group_auto_done_setting',
            'sale.group_services_and_material',
            'sale.group_warning_sale',
        )
