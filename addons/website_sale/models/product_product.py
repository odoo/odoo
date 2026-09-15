from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"
    _mail_post_access = "read"

    variant_ribbon_id = fields.Many2one(comodel_name="product.ribbon")
    website_id = fields.Many2one(
        related="product_tmpl_id.website_id",
        readonly=False,
    )

    product_variant_image_ids = fields.One2many(
        comodel_name="product.image",
        inverse_name="product_variant_id",
        string="Extra Variant Images",
    )

    base_unit_count = fields.Float(
        default=1,
        required=True,
        help="Display base unit price on your eCommerce pages. Set to 0 to hide it for this"
        " product.",
    )
    base_unit_id = fields.Many2one(
        comodel_name="website.base.unit",
        string="Custom Unit of Measure",
        help="Define a custom unit to display in the price per unit of measure field.",
    )
    base_unit_price = fields.Monetary(
        string="Price Per Unit",
        compute="_compute_base_unit_price",
    )
    base_unit_name = fields.Char(
        compute="_compute_base_unit_name",
        help="Displays the custom unit for the products if defined or the selected unit of measure"
        " otherwise.",
    )

    website_url = fields.Char(
        string="Website URL",
        compute="_compute_product_website_url",
        help="The full URL to access the document through the website.",
    )

    def _get_base_unit_price(self, price):
        self.check_singleton()
        return self.base_unit_count and price / self.base_unit_count

    @api.depends("lst_price", "base_unit_count")
    def _compute_base_unit_price(self):
        for product in self:
            if not product.id:
                product.base_unit_price = 0
            else:
                product.base_unit_price = product._get_base_unit_price(
                    product.lst_price
                )

    @api.depends("uom_name", "base_unit_id")
    def _compute_base_unit_name(self):
        for product in self:
            product.base_unit_name = product.base_unit_id.name or product.uom_name

    @api.depends_context("lang")
    @api.depends("product_tmpl_id.website_url", "product_template_attribute_value_ids")
    def _compute_product_website_url(self):
        for product in self:
            url = product.product_tmpl_id.website_url
            if (
                pavs
                := product.product_template_attribute_value_ids.product_attribute_value_id
            ):
                pav_ids = [str(pav.id) for pav in pavs]
                url = f"{url}?attribute_values={','.join(pav_ids)}"
            product.website_url = url

    @api.constrains("base_unit_count")
    def _check_base_unit_count(self):
        if any(product.base_unit_count < 0 for product in self):
            _debug.logic("base_unit_count_refused", products=self)
            raise ValidationError(
                _(
                    "The value of Base Unit Count must be greater than 0."
                    " Use 0 to hide the price per unit on this product."
                )
            )

    def website_publish_button(self):
        self.check_singleton()
        return self.product_tmpl_id.website_publish_button()

    def open_website_url(self):
        self.check_singleton()
        res = self.product_tmpl_id.open_website_url()
        res["url"] = self.website_url
        return res

    def _get_images(self):
        self.check_singleton()
        variant_images = list(self.product_variant_image_ids)
        template_images = list(self.product_tmpl_id.product_template_image_ids)
        return [self] + variant_images + template_images

    def _get_combination_info_variant(self, **kwargs):
        self.check_singleton()
        return self.product_tmpl_id._get_combination_info(
            combination=self.product_template_attribute_value_ids,
            product_id=self.id,
            **kwargs,
        )

    def _website_show_quick_add(self):
        self.check_singleton()
        if not self.filtered_domain(self.env["website"]._product_domain()):
            return False
        return (
            not request.website.prevent_zero_price_sale or self._get_contextual_price()
        )

    def _is_add_to_cart_allowed(self):
        self.check_singleton()
        if self.env.user.has_group("base.group_system"):
            return True
        if not self.active or not self.website_published:
            _debug.logic("add_to_cart_denied", reason="unpublished", product=self.id)
            return False
        if not self.filtered_domain(self.env["website"]._product_domain()):
            _debug.logic(
                "add_to_cart_denied", reason="outside_product_domain", product=self.id
            )
            return False
        if request.website.prevent_zero_price_sale and not self._get_contextual_price():
            _debug.logic("add_to_cart_denied", reason="zero_price", product=self.id)
            return False
        return request.website.has_ecommerce_access()

    @api.onchange("public_categ_ids")
    def _onchange_public_categ_ids(self):
        if self.public_categ_ids:
            self.website_published = True
        else:
            self.website_published = False

    def _to_markup_data(self, website):
        self.check_singleton()

        product_price = request.pricelist._get_product_price(
            self, quantity=1, currency=website.currency_id
        )
        product_taxes_sudo = self.sudo().taxes_id._filter_taxes_by_company(
            self.env.company
        )
        taxes = request.fiscal_position.map_tax(product_taxes_sudo)
        price = self.product_tmpl_id._apply_taxes_to_price(
            product_price,
            website.currency_id,
            product_taxes_sudo,
            taxes,
            self,
            website=website,
        )

        base_url = website.get_base_url()
        markup_data = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": self.with_context(display_default_code=False).display_name,
            "url": f"{base_url}{self.website_url}",
            "image": f"{base_url}{website.image_url(self, 'image_1920')}",
            "offers": {
                "@type": "Offer",
                "price": price,
                "priceCurrency": website.currency_id.name,
            },
        }
        if self.website_meta_description or self.description_sale:
            markup_data["description"] = (
                self.website_meta_description or self.description_sale
            )
        if website.is_view_active("website_sale.product_comment") and self.rating_count:
            markup_data["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": self.sudo().rating_avg,
                "reviewCount": self.rating_count,
            }
        return markup_data

    def _get_image_1920_url(self):
        self.check_singleton()
        return self.env["website"].image_url(self, "image_1920")

    def _get_extra_image_1920_urls(self):
        self.check_singleton()
        return [
            self.env["website"].image_url(extra_image, "image_1920")
            for extra_image in self.product_variant_image_ids
            + self.product_template_image_ids
            if extra_image.image_128
        ]

    def write(self, vals):
        if "active" in vals and not vals["active"]:
            self.env["sale.order.line"].sudo().search(
                [
                    ("state", "=", "draft"),
                    ("product_id", "in", self.ids),
                    ("order_id", "any", [("website_id", "!=", False)]),
                ]
            ).unlink()
        return super().write(vals)
