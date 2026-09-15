from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog

from odoo.addons.sale_gelato import utils

_debug = DebugLog(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    gelato_template_ref = fields.Char(
        string="Gelato Template Reference",
        help="Synchronize to fetch variants from Gelato",
    )
    gelato_product_uid = fields.Char(
        string="Gelato Product UID",
        compute="_compute_gelato_product_uid",
        inverse="_inverse_gelato_product_uid",
        readonly=True,
    )
    gelato_image_ids = fields.One2many(
        comodel_name="document.document",
        inverse_name="res_id",
        string="Gelato Print Images",
        readonly=True,
        domain=[("is_gelato", "=", True)],
    )
    gelato_missing_images = fields.Boolean(
        string="Missing Print Images",
        compute="_compute_gelato_missing_images",
    )

    @api.depends("product_variant_ids.gelato_product_uid")
    def _compute_gelato_product_uid(self):
        self._compute_template_field_from_variant_field("gelato_product_uid")

    def _inverse_gelato_product_uid(self):
        self._set_product_variant_field("gelato_product_uid")

    @api.depends("gelato_image_ids")
    def _compute_gelato_missing_images(self):
        for product in self:
            product.gelato_missing_images = any(
                not image.datas for image in product.gelato_image_ids
            )

    def action_sync_gelato_template_info(self):
        try:
            endpoint = f"templates/{self.gelato_template_ref}"
            template_info = utils.send_request(
                self.env.company.sudo().gelato_api_key,
                "ecommerce",
                "v1",
                endpoint,
                method="GET",
            )
        except UserError as e:
            _debug.logic("gelato_template_sync_failed", template=self, error=str(e))
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "danger",
                    "title": _("Could not synchronize with Gelato"),
                    "message": str(e),
                    "sticky": True,
                },
            }

        _debug.pipeline(
            "gelato_template_synced",
            template=self,
            variants=len(template_info["variants"]),
        )
        self._create_attributes_from_gelato_info(template_info)
        self._create_print_images_from_gelato_info(template_info)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Successfully synchronized with Gelato"),
                "message": _(
                    "Missing product variants and images have been successfully created."
                ),
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    def _create_attributes_from_gelato_info(self, template_info):
        if len(template_info["variants"]) == 1:
            _debug.logic("gelato_single_variant", template=self)
            self.gelato_product_uid = template_info["variants"][0]["productUid"]
        else:
            for variant_data in template_info["variants"]:
                current_variant_pavs = self.env["product.attribute.value"]
                for attribute_data in variant_data["variantOptions"]:
                    attribute = self.env["product.attribute"].search(  # noqa: E8507 - one lookup per Gelato attribute; the record may have been created by an earlier pass
                        [
                            ("name", "=", attribute_data["name"]),
                            ("create_variant", "=", "always"),
                        ],
                        limit=1,
                    )
                    if not attribute:
                        attribute = self.env["product.attribute"].create(
                            {"name": attribute_data["name"]}
                        )

                    attribute_value = self.env["product.attribute.value"].search(  # noqa: E8507 - one lookup per Gelato attribute; the record may have been created by an earlier pass
                        [
                            ("name", "=", attribute_data["value"]),
                            ("attribute_id", "=", attribute.id),
                        ],
                        limit=1,
                    )
                    if not attribute_value:
                        attribute_value = self.env["product.attribute.value"].create(
                            {
                                "name": attribute_data["value"],
                                "attribute_id": attribute.id,
                            }
                        )
                    current_variant_pavs += attribute_value

                    ptal = self.env["product.template.attribute.line"].search(  # noqa: E8507 - one lookup per Gelato attribute; the record may have been created by an earlier pass
                        [
                            ("product_tmpl_id", "=", self.id),
                            ("attribute_id", "=", attribute.id),
                        ],
                        limit=1,
                    )
                    if not ptal:
                        self.env["product.template.attribute.line"].create(
                            {
                                "product_tmpl_id": self.id,
                                "attribute_id": attribute.id,
                                "value_ids": [Command.link(attribute_value.id)],
                            }
                        )
                    else:
                        ptal.value_ids = [Command.link(attribute_value.id)]

                for variant in self.product_variant_ids:
                    corresponding_ptavs = variant.product_template_attribute_value_ids
                    corresponding_pavs = corresponding_ptavs.product_attribute_value_id
                    if corresponding_pavs == current_variant_pavs:
                        variant.gelato_product_uid = variant_data["productUid"]
                        break

            variants_without_gelato = self.env["product.product"].search(
                [("product_tmpl_id", "=", self.id), ("gelato_product_uid", "=", False)]
            )
            variants_without_gelato.unlink()

    def _create_print_images_from_gelato_info(self, template_info):
        for print_image_data in template_info["variants"][0]["imagePlaceholders"]:
            if print_image_data["printArea"].lower() in ("1", "front"):
                print_image_data["printArea"] = "default"

            print_image_found = bool(
                self.env["document.document"].search_count(  # noqa: E8507 - one lookup per Gelato attribute; the record may have been created by an earlier pass
                    [
                        ("name", "ilike", print_image_data["printArea"]),
                        ("res_id", "=", self.id),
                        ("res_model", "=", "product.template"),
                        (
                            "is_gelato",
                            "=",
                            True,
                        ),
                    ],
                    limit=1,
                )
            )
            if not print_image_found:
                self.gelato_image_ids = [
                    Command.create(
                        {
                            "name": print_image_data["printArea"].lower(),
                            "res_id": self.id,
                            "res_model": "product.template",
                            "is_gelato": True,
                        }
                    )
                ]

    def _get_related_fields_variant_template(self):
        return super()._get_related_fields_variant_template() + ["gelato_product_uid"]

    def _get_domain_product_document(self):
        return super()._get_domain_product_document() & Domain("is_gelato", "=", False)
