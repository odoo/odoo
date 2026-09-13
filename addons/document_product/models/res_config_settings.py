from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    documents_product_settings = fields.Boolean(
        related="company_id.documents_product_settings",
        string="Product",
        readonly=False,
    )
    product_folder_id = fields.Many2one(
        comodel_name="document.document",
        related="company_id.product_folder_id",
        string="product default folder",
        readonly=False,
    )
    product_tag_ids = fields.Many2many(
        comodel_name="document.tag",
        related="company_id.product_tag_ids",
        string="Product Tags",
        readonly=False,
    )
