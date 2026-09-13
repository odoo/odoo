from odoo import fields, models


class WebsiteTrack(models.Model):
    _inherit = "website.track"

    product_id = fields.Many2one(
        comodel_name="product.product",
        index="btree_not_null",
        readonly=True,
        ondelete="cascade",
    )
