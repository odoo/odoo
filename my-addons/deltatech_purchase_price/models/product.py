# ©  2015-2019 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import api, models


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = "product.template"

    @api.depends("property_cost_method", "categ_id.property_cost_method")
    def _compute_cost_method(self):
        super(ProductTemplate, self)._compute_cost_method()
        if self.cost_method == "fifo" and self.env.context.get("force_fifo_to_average", False):
            self.cost_method = "average"
