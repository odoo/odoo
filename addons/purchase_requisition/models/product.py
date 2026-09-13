from odoo import fields, models


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    purchase_requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        related="purchase_requisition_line_id.requisition_id",
        string="Agreement",
    )
    purchase_requisition_line_id = fields.Many2one(
        comodel_name="purchase.requisition.line",
        index="btree_not_null",
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _prepare_sellers(self, params=False):
        sellers = super()._prepare_sellers(params=params)
        if (
            params
            and params.get("order_id")
            and params["order_id"]._fields.get("requisition_id")
        ):
            return sellers.filtered(
                lambda s: (
                    not s.purchase_requisition_id
                    or s.purchase_requisition_id == params["order_id"].requisition_id
                )
            )
        else:
            return sellers
