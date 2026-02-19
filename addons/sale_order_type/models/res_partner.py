# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    sale_type = fields.Many2one(
        comodel_name="sale.order.type", string="Sale Order Type", company_dependent=True
    )

    def copy_data(self, default=None):
        result = super().copy_data(default=default)
        for idx, partner in enumerate(self):
            values = result[idx]
            if partner.sale_type and not values.get("sale_type"):
                values["sale_type"] = partner.sale_type
        return result
