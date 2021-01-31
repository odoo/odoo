# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def unlink(self):
        product_id = self.env["ir.config_parameter"].sudo().get_param("sale.default_deposit_product_id")
        for line in self:
            if product_id and line.product_id.id == int(product_id) and line.qty_invoiced == 0:
                self -= line
                super(models.Model, line).unlink()
        return super(SaleOrderLine, self).unlink()
