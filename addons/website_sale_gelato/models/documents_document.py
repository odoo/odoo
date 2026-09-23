from odoo import api, models
from odoo.exceptions import ValidationError


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    @api.constrains("datas")
    def _check_product_is_unpublished_before_removing_print_images(self):
        for print_image in self.filtered(lambda i: i.is_gelato):
            template = self.env["product.template"].browse(print_image.res_id)
            if template.is_published and not print_image.datas:
                raise ValidationError(
                    self.env._(
                        "Products must be unpublished before print images can be removed."
                    )
                )
