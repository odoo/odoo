from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.constrains("is_published")
    def _check_print_images_are_set_before_publishing(self):
        for product in self.filtered("gelato_template_ref"):
            if product.is_published and product.gelato_missing_images:
                raise ValidationError(
                    _(
                        "Print images must be set on products before they can be published."
                    )
                )

    def action_sync_gelato_template_info(self):
        image_count_before_sync = len(self.gelato_image_ids)
        res = super().action_sync_gelato_template_info()
        if image_count_before_sync < len(self.gelato_image_ids):
            _debug.lifecycle(
                "unpublished_after_gelato_sync",
                product=self,
                before=image_count_before_sync,
                after=len(self.gelato_image_ids),
            )
            self.is_published = False
        return res

    def _create_attributes_from_gelato_info(self, template_info):
        self.description_ecommerce = template_info["description"]
        return super()._create_attributes_from_gelato_info(template_info)
