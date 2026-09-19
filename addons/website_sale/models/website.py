import base64
import json
import logging
from urllib.parse import urlsplit, urlunsplit

from lxml import etree
from werkzeug.exceptions import NotFound

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import AccessError, MissingError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools import file_open, ormcache
from odoo.tools.translate import LazyTranslate, _

from odoo.addons.website_sale import const

logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)
_lt = LazyTranslate(__name__)


CART_SESSION_CACHE_KEY = "sale_order_id"
FISCAL_POSITION_SESSION_CACHE_KEY = "fiscal_position_id"
PRICELIST_SESSION_CACHE_KEY = "website_sale_current_pl"
PRICELIST_SELECTED_SESSION_CACHE_KEY = "website_sale_selected_pl_id"


class Website(models.Model):
    _inherit = "website"

    def _default_salesteam_id(self):
        team = self.env.ref(
            "sale_team.salesteam_website_sales", raise_if_not_found=False
        )
        if team and team.active:
            return team.id
        return None

    def _default_cart_recovery_mail_template_id(self):
        try:
            return self.env.ref("website_sale.mail_template_sale_cart_recovery").id
        except ValueError:
            return False

    def _default_confirmation_email_template_id(self):
        template_id = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sale.default_confirmation_template")
        )
        default_template = (
            template_id and self.env["mail.template"].browse(int(template_id)).exists()
        )
        if default_template:
            return default_template
        return self.env.ref(
            "sale.mail_template_sale_confirmation", raise_if_not_found=False
        )

    salesperson_id = fields.Many2one(
        comodel_name="res.users",
        domain=[("share", "=", False)],
    )
    salesteam_id = fields.Many2one(
        comodel_name="team.team",
        string="Sales Team",
        default=_default_salesteam_id,
        index="btree_not_null",
        domain=[("use_sale", "=", True)],
        ondelete="set null",
    )
    show_line_subtotals_tax_selection = fields.Selection(
        selection=[
            ("tax_excluded", "Tax Excluded"),
            ("tax_included", "Tax Included"),
        ],
        string="Line Subtotals Tax Display",
        compute="_compute_show_line_subtotals_tax_selection",
        store=True,
        readonly=False,
    )

    add_to_cart_action = fields.Selection(
        selection=[
            ("stay", "Stay on Product Page"),
            ("go_to_cart", "Go to cart"),
        ],
        default="stay",
    )
    auth_signup_uninvited = fields.Selection(default="b2c")
    account_on_checkout = fields.Selection(
        selection=[
            ("optional", "Optional"),
            ("disabled", "Disabled (buy as guest)"),
            ("mandatory", "Mandatory (no guest checkout)"),
        ],
        string="Customer Accounts",
        default="optional",
    )
    cart_recovery_mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Cart Recovery Email",
        default=_default_cart_recovery_mail_template_id,
        domain=[("model", "=", "sale.order")],
    )
    contact_us_button_url = fields.Char(
        string="Contact Us Button URL",
        translate=True,
        default="/contactus",
    )
    cart_abandoned_delay = fields.Float(
        string="Abandoned Delay",
        default=10.0,
    )
    send_abandoned_cart_email = fields.Boolean(
        string="Send email to customers who abandoned their cart."
    )
    send_abandoned_cart_email_activation_time = fields.Datetime(
        string="Time when the 'Send abandoned cart email' feature was activated.",
        compute="_compute_send_abandoned_cart_email_activation_time",
        store=True,
    )
    shop_page_container = fields.Selection(
        selection=[
            ("regular", "Regular"),
            ("fluid", "Full-width"),
        ],
        default="regular",
    )
    shop_ppg = fields.Integer(
        string="Number of products in the grid on the shop",
        default=21,
    )
    shop_ppr = fields.Integer(
        string="Number of grid columns on the shop",
        default=3,
    )

    shop_gap = fields.Char(
        string="Grid-gap on the shop",
        default="16px",
        required=False,
    )

    shop_opt_products_design_classes = fields.Char(
        string="Shop Design Class",
        default="o_wsale_products_opt_layout_catalog o_wsale_products_opt_design_thumbs "
        "o_wsale_products_opt_name_color_regular o_wsale_products_opt_rounded_2 "
        "o_wsale_products_opt_thumb_cover o_wsale_products_opt_img_secondary_show "
        "o_wsale_products_opt_img_hover_zoom_out_light o_wsale_products_opt_has_cta "
        "o_wsale_products_opt_actions_onhover o_wsale_products_opt_has_wishlist "
        "o_wsale_products_opt_wishlist_fixed o_wsale_products_opt_has_description "
        "o_wsale_products_opt_actions_subtle o_wsale_products_opt_cc1",
        help="CSS class for shop products design",
    )

    shop_default_sort = fields.Selection(
        selection="_selection_product_sorts",
        default="website_sequence asc",
        required=True,
    )

    shop_extra_field_ids = fields.One2many(
        comodel_name="website.sale.extra.field",
        inverse_name="website_id",
        string="E-Commerce Extra Fields",
    )

    product_page_container = fields.Selection(
        selection=[
            ("unset", "Unset"),
            ("regular", "Regular"),
            ("fluid", "Full-width"),
        ],
        default="unset",
    )

    product_page_cols_order = fields.Selection(
        selection=[
            ("regular", "Regular order"),
            ("inverse", "Inverse order"),
        ],
        string="Product Page main columns order",
        default="regular",
    )

    product_page_image_layout = fields.Selection(
        selection=[
            ("carousel", "Carousel"),
            ("grid", "Grid"),
        ],
        default="carousel",
        required=True,
    )
    product_page_image_width = fields.Selection(
        selection=[
            ("none", "Hidden"),
            ("33_pc", "33 %"),
            ("50_pc", "50 %"),
            ("66_pc", "66 %"),
            ("100_pc", "100 %"),
        ],
        default="50_pc",
        required=True,
    )
    product_page_image_spacing = fields.Selection(
        selection=[
            ("none", "None"),
            ("small", "Small"),
            ("medium", "Medium"),
            ("big", "Big"),
        ],
        default="none",
        required=True,
    )
    product_page_image_roundness = fields.Selection(
        selection=[
            ("none", "None"),
            ("small", "Small"),
            ("medium", "Medium"),
            ("big", "Big"),
        ],
        default="none",
        required=True,
    )
    product_page_image_ratio = fields.Selection(
        selection=[
            ("auto", "Auto"),
            ("21_9", "Wider (21/9)"),
            ("16_9", "Wide (16/9)"),
            ("4_3", "Landscape (4/3)"),
            ("6_5", "Horizontal (6/5)"),
            ("1_1", "Default (1/1)"),
            ("4_5", "Portrait (4/5)"),
            ("2_3", "Vertical (2/3)"),
        ],
        default="1_1",
        required=True,
    )
    product_page_image_ratio_mobile = fields.Selection(
        selection=[
            ("auto", "Auto"),
            ("21_9", "Wider (21/9)"),
            ("16_9", "Wide (16/9)"),
            ("4_3", "Landscape (4/3)"),
            ("6_5", "Horizontal (6/5)"),
            ("1_1", "Default (1/1)"),
            ("4_5", "Portrait (4/5)"),
            ("2_3", "Vertical (2/3)"),
        ],
        default="auto",
        required=True,
    )
    ecommerce_access = fields.Selection(
        selection=[
            ("everyone", "All users"),
            ("logged_in", "Logged in users"),
        ],
        default="everyone",
        required=True,
    )
    product_page_grid_columns = fields.Integer(default=2)

    prevent_zero_price_sale = fields.Boolean(string="Hide 'Add To Cart' when price = 0")

    enabled_gmc_src = fields.Boolean(
        string="Google Merchant Center",
        default=lambda self: self.env["res.groups"]._is_feature_enabled(
            "website_sale.group_product_feed",
        ),
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Default Currency",
        compute="_compute_currency_id",
    )
    pricelist_ids = fields.One2many(
        comodel_name="product.pricelist",
        string="Price list available for this Ecommerce/Website",
        compute="_compute_pricelist_ids",
    )
    confirmation_email_template_id = fields.Many2one(
        comodel_name="mail.template",
        default=_default_confirmation_email_template_id,
        domain=[("model", "=", "sale.order")],
    )

    def _compute_pricelist_ids(self):
        for website in self:
            website = website.with_company(website.company_id)
            ProductPricelist = website.env["product.pricelist"]
            website.pricelist_ids = ProductPricelist.sudo().search_fetch(  # noqa: E8507 - one query per website, in that website's company
                ProductPricelist._get_domain_website_pricelists(website)
            )

    @api.depends("company_id")
    def _compute_currency_id(self):
        for website in self:
            website.currency_id = (
                request
                and hasattr(request, "pricelist")
                and request.pricelist.currency_id
            ) or website.company_id.sudo().currency_id

    @api.depends("send_abandoned_cart_email")
    def _compute_send_abandoned_cart_email_activation_time(self):
        for website in self:
            if website.send_abandoned_cart_email:
                website.send_abandoned_cart_email_activation_time = (
                    fields.Datetime.now()
                )

    @api.depends("company_id.account_config_id.account_fiscal_country_id")
    def _compute_show_line_subtotals_tax_selection(self):
        for website in self:
            website.show_line_subtotals_tax_selection = "tax_excluded"

    @staticmethod
    def _selection_product_sorts():
        return [
            ("website_sequence asc", _("Featured")),
            ("publish_date desc", _("Newest Arrivals")),
            ("name asc", _("Name (A-Z)")),
            ("list_price asc", _("Price - Low to High")),
            ("list_price desc", _("Price - High to Low")),
        ]

    @api.model
    def get_configurator_shop_page_styles(self):
        return [
            {"option": option, "img_src": config["img_src"], "title": config["title"]}
            for option, config in const.SHOP_PAGE_STYLE_MAPPING.items()
        ]

    @api.model
    def get_configurator_product_page_styles(self):
        return [
            {"option": option, "img_src": config["img_src"], "title": config["title"]}
            for option, config in const.PRODUCT_PAGE_STYLE_MAPPING.items()
        ]

    @api.model
    def configurator_apply(
        self, *, shop_page_style_option=None, product_page_style_option=None, **kwargs
    ):
        res = super().configurator_apply(**kwargs)

        website = self.get_current_website()
        website_settings = {}
        category_settings = {}
        views_to_disable = []
        views_to_enable = []
        scss_customization_params = {}
        ThemeUtils = self.env["theme.utils"].with_context(website_id=website.id)
        Assets = self.env["website.assets"]

        def parse_style_config(style_config_):
            website_settings.update(style_config_["website_fields"])
            category_settings.update(style_config_.get("category_fields", {}))
            views_to_disable.extend(style_config_["views"]["disable"])
            views_to_enable.extend(style_config_["views"]["enable"])
            scss_customization_params.update(
                style_config_.get("scss_customization_params", {})
            )

        if shop_page_style_option:
            style_config = const.SHOP_PAGE_STYLE_MAPPING[shop_page_style_option]
            parse_style_config(style_config)

        if product_page_style_option:
            style_config = const.PRODUCT_PAGE_STYLE_MAPPING[product_page_style_option]
            parse_style_config(style_config)

        if website_settings:
            website.write(website_settings)
        if category_settings:
            self.env["product.public.category"].search(website.website_domain()).write(
                category_settings
            )
        for xml_id in views_to_disable:
            ThemeUtils.disable_view(xml_id)
        for xml_id in views_to_enable:
            ThemeUtils.enable_view(xml_id)

        for footer_id in ThemeUtils._footer_templates:
            footer_view = self.with_context(website_id=website.id).viewref(
                footer_id,
                raise_if_not_found=False,
            )
            if not footer_view.active:
                continue

            footer_updated = False
            try:
                arch_tree = etree.fromstring(footer_view.arch)
            except etree.XMLSyntaxError as e:
                logger.warning(
                    "Failed to update ecommerce footer view %s: %s", footer_id, e
                )
            else:
                footer_div_node = arch_tree.xpath(
                    "//section/div[hasclass('container') or hasclass('o_container_small') or hasclass('container-fluid')]",
                )
                if not footer_div_node:
                    logger.warning(
                        "Failed to match footer width with header in ecommerce footer view %s",
                        footer_id,
                    )
                elif "website.footer_copyright_content_width_fluid" in views_to_enable:
                    footer_updated = True
                    footer_div_node[0].set("class", "container-fluid s_allow_columns")
                elif "website.footer_copyright_content_width_small" in views_to_enable:
                    footer_updated = True
                    footer_div_node[0].set("class", "o_container_small s_allow_columns")

                if footer_id == "website_sale.template_footer_website_sale":
                    ecommerce_categories_node = arch_tree.xpath(
                        "//t[@t-set='ecommerce_categories']"
                    )
                    if not ecommerce_categories_node:
                        logger.warning(
                            "Skipping ecommerce categories in ecommerce footer view %s",
                            footer_id,
                        )
                    else:
                        ecommerce_categories = self.env[
                            "product.public.category"
                        ].search([], limit=6)  # noqa: E8507 - runs for the one ecommerce footer of the list
                        footer_updated = True
                        ecommerce_categories_node[0].attrib["t-value"] = json.dumps(
                            [
                                {
                                    "name": cat.name,
                                    "id": cat.id,
                                }
                                for cat in ecommerce_categories
                            ]
                        )

                if footer_updated:
                    footer_view.write({"arch": etree.tostring(arch_tree)})

        if "website_sale.template_footer_website_sale" in views_to_enable:
            scss_customization_params["footer-template"] = "website_sale"

        if scss_customization_params:
            Assets.update_scss_customization(
                "/website/static/src/scss/options/user_values.scss",
                scss_customization_params,
            )

        return res

    def configurator_addons_apply(self, industry_name=None, **kwargs):

        def generate_categories(industry_name_):
            lang = self.env.context.get("lang")
            prompt = (
                f"You are a seasoned Marketing Expert specializing in crafting high-converting eCommerce experiences.\n"
                f"Your task is to develop compelling category names and descriptions for a {industry_name_}'s new online store.\n"
                f"The goal is to create categories that are persuasive, attention-grabbing, and concise, encouraging visitors to explore the offerings.\n"
                f"All content should be in {lang}.\n"
                f"Here's the format you will use to generate the categories:\n"
                f'{{"categories": ['
                f'{{"name": "$category_name_1", "description": "$category_description_1"}}, '
                f'{{"name": "$category_name_2", "description": "$category_description_2"}}, '
                f'{{"name": "$category_name_3", "description": "$category_description_3"}}, '
                f'{{"name": "$category_name_4", "description": "$category_description_4"}}, '
                f'{{"name": "$category_name_5", "description": "$category_description_5"}}, '
                f'{{"name": "$category_name_6", "description": "$category_description_6"}}, '
                f'{{"name": "$category_name_7", "description": "$category_description_7"}}, '
                f'{{"name": "$category_name_8", "description": "$category_description_8"}}'
                f"]}}\n"
                f"Constraints:\n"
                f"Language: {lang}\n"
                f"Category Names: Must be nouns only (no adjectives).\n"
                f"Description Length: Keep descriptions very short and to the point (ideally under 20 words).\n"
                f"Persuasion: Descriptions should be persuasive and designed to attract attention.\n"
                f"Number of Categories: Exactly 8 categories are required.\n"
                f"Now, generate the 8 eCommerce categories for the {industry_name_}, adhering to the specified format and constraints."
            )
            IrConfigParameterSudo = self.env["ir.config_parameter"].sudo()
            database_id = IrConfigParameterSudo.get_param("database.uuid")
            try:
                response = self._OLG_api_rpc(
                    "/api/olg/1/chat",
                    {
                        "prompt": prompt,
                        "conversation_history": [],
                        "database_id": database_id,
                    },
                )
            except AccessError:
                logger.warning("API is unreachable for the category generation")
                return None

            if response["status"] == "success":
                content = (
                    response["content"].replace("```json\n", "").replace("\n```", "")
                )
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.warning(
                        "API response is not a valid JSON for the category generation"
                    )
            elif response["status"] == "error_prompt_too_long":
                logger.warning("Prompt is too long for the category generation")
            elif response["status"] == "limit_call_reached":
                logger.warning("Limit call reached for the category generation")
            else:
                logger.warning(
                    "Response could not be generated for the category generation"
                )
            return None

        res = super().configurator_addons_apply(industry_name=industry_name, **kwargs)

        if self.env["product.public.category"].search_count([], limit=1):
            logger.info("Categories already exist, skipping AI generation.")
            return None

        category_specs = generate_categories(industry_name)
        if not isinstance(category_specs, dict):
            return None

        if len(category_specs.get("categories")) == 8:
            images_names = [f"shape_mixed_{i}.png" for i in range(1, 9)]
            categories = []
            for idx, cat in enumerate(category_specs["categories"]):
                image_name = images_names[idx]
                img_path = "website_sale/static/src/img/categories/" + image_name
                with file_open(img_path, "rb") as file:
                    image_base64 = base64.b64encode(file.read())
                categories.append(
                    {
                        "name": cat["name"],
                        "website_description": cat["description"],
                        "image_1920": image_base64,
                        "cover_image": image_base64,
                    }
                )
            self.env["product.public.category"].sudo().create(categories)
        return res

    @ormcache(
        "country_code",
        "show_visible",
        "current_pl_id",
        "website_pricelist_ids",
        "partner_pl_id",
    )
    def _get_pl_partner_order(
        self,
        country_code,
        show_visible,
        current_pl_id,
        website_pricelist_ids,
        partner_pl_id=False,
    ):
        self.check_singleton()
        pricelists = self.env["product.pricelist"]

        def check_pricelist(pricelist):
            if show_visible:
                return pricelist.selectable or pricelist.id == current_pl_id
            else:
                return True

        if country_code:
            pricelists |= (
                self.env["res.country.group"]
                .search([("country_ids.code", "=", country_code)])
                .pricelist_ids.filtered(
                    lambda pl: pl._is_available_on_website(self) and check_pricelist(pl)
                )
            )

        if not pricelists:
            pricelists = pricelists.browse(website_pricelist_ids).filtered(
                lambda pl: (
                    check_pricelist(pl) and not (country_code and pl.country_group_ids)
                )
            )

        if not self.env.user._is_public():
            partner_pricelist = pricelists.browse(partner_pl_id).filtered(
                lambda pl: (
                    pl._is_available_on_website(self)
                    and check_pricelist(pl)
                    and pl._is_available_in_country(country_code)
                )
            )
            pricelists |= partner_pricelist

        _debug.perf.count(
            "pricelists_available",
            website=self.id,
            country=country_code or None,
            visible_only=show_visible,
            pricelists=len(pricelists),
        )
        return pricelists.sudo().sorted().ids

    def get_pricelist_available(self, show_visible=False):
        self.check_singleton()

        ProductPricelist = self.env["product.pricelist"]

        if not self.env["res.groups"]._is_feature_enabled(
            "product.group_product_pricelist"
        ):
            _debug.logic("pricelists_disabled", website=self.id)
            return ProductPricelist

        country_code = self._get_geoip_country_code()
        website = self.with_company(self.company_id)

        partner_sudo = website.env.user.partner_id
        is_user_public = self.env.user._is_public()
        if not is_user_public:
            ctx = {"country_code": country_code} if country_code else {}
            partner_pricelist_id = partner_sudo.with_context(
                **ctx
            ).property_product_pricelist.id
        else:
            partner_pricelist_id = False
        website_pricelists = website.sudo().pricelist_ids

        current_pricelist_id = (
            request and request.session.get(PRICELIST_SESSION_CACHE_KEY)
        ) or None

        pricelist_ids = website._get_pl_partner_order(
            country_code,
            show_visible,
            current_pl_id=current_pricelist_id,
            website_pricelist_ids=tuple(website_pricelists.ids),
            partner_pl_id=partner_pricelist_id,
        )

        return ProductPricelist.browse(pricelist_ids)

    def is_pricelist_available(self, pl_id):
        return pl_id in self.get_pricelist_available(show_visible=False).ids

    def _get_geoip_country_code(self):
        return (request and request.geoip.country_code) or False

    def sale_product_domain(self):
        website_domain = self.get_current_website().website_domain()
        if self.env.user._is_internal():
            user_domain = Domain.TRUE
        else:
            user_domain = [
                ("is_published", "=", True),
                (
                    "service_tracking",
                    "in",
                    self.env["product.template"]._get_saleable_tracking_types(),
                ),
            ]
        return Domain.AND([self._product_domain(), website_domain, user_domain])

    def _product_domain(self):
        return [("sale_ok", "=", True)]

    def _create_cart(self):
        self.check_singleton()

        partner_sudo = self.env.user.partner_id

        so_data = self._prepare_sale_order_values(partner_sudo)
        sale_order_sudo = (
            self.env["sale.order"]
            .with_user(SUPERUSER_ID)
            .with_company(self.company_id)
            .create(so_data)
        )

        sale_order_sudo = sale_order_sudo.with_user(self.env.user).sudo()

        _debug.lifecycle(
            "cart_created",
            website=self.id,
            order=sale_order_sudo.id,
            partner=partner_sudo.id,
        )
        request.session[CART_SESSION_CACHE_KEY] = sale_order_sudo.id
        request.session["website_sale_cart_quantity"] = sale_order_sudo.cart_quantity
        request.cart = sale_order_sudo

        return sale_order_sudo

    def _prepare_sale_order_values(self, partner_sudo):
        self.check_singleton()

        return {
            "company_id": self.company_id.id,
            "partner_id": partner_sudo.id,
            "fiscal_position_id": request.fiscal_position.id,
            "pricelist_id": request.pricelist.id,
            "team_id": self.salesteam_id.id,
            "website_id": self.id,
        }

    def _get_and_cache_current_pricelist(self):
        self.check_singleton()

        ProductPricelistSudo = self.env["product.pricelist"].sudo()
        if not self.env["res.groups"]._is_feature_enabled(
            "product.group_product_pricelist"
        ):
            return ProductPricelistSudo

        if PRICELIST_SESSION_CACHE_KEY in request.session:
            pricelist_sudo = ProductPricelistSudo.browse(
                request.session[PRICELIST_SESSION_CACHE_KEY]
            )
            if pricelist_sudo and (
                pricelist_sudo.exists()
                and pricelist_sudo._is_available_on_website(self)
                and pricelist_sudo._is_available_in_country(
                    self._get_geoip_country_code()
                )
            ):
                return pricelist_sudo.sudo()

        if cart_sudo := request.cart:
            if not request.env.cr.readonly:
                cart_sudo._compute_pricelist_id()
            pricelist_sudo = cart_sudo.pricelist_id
        else:
            pricelist_sudo = self.env.user.partner_id.property_product_pricelist
            available_pricelists = self.get_pricelist_available()
            if available_pricelists and pricelist_sudo not in available_pricelists:
                pricelist_sudo = available_pricelists[0].sudo()

        request.session[PRICELIST_SESSION_CACHE_KEY] = pricelist_sudo.id

        return pricelist_sudo

    def _get_and_cache_current_fiscal_position(self):
        self.check_singleton()

        AccountFiscalPositionSudo = self.env["account.fiscal.position"].sudo()
        fpos_sudo = AccountFiscalPositionSudo

        if FISCAL_POSITION_SESSION_CACHE_KEY in request.session:
            fpos_sudo = AccountFiscalPositionSudo.browse(
                request.session[FISCAL_POSITION_SESSION_CACHE_KEY]
            )
            if fpos_sudo and fpos_sudo.exists():
                return fpos_sudo

        partner_sudo = self.env.user.partner_id

        if (
            request
            and request.geoip.country_code
            and self.partner_id.id == partner_sudo.id
        ):
            country = self.env["res.country"].search(
                [("code", "=", request.geoip.country_code)],
                limit=1,
            )
            partner_geoip = (
                self.env["res.partner"].sudo().new({"country_id": country.id})
            )
            fpos_sudo = AccountFiscalPositionSudo._get_fiscal_position(partner_geoip)

        if not fpos_sudo:
            fpos_sudo = AccountFiscalPositionSudo._get_fiscal_position(partner_sudo)

        request.session[FISCAL_POSITION_SESSION_CACHE_KEY] = fpos_sudo.id

        return fpos_sudo

    def _get_and_cache_current_cart(self):
        self.check_singleton()

        SaleOrderSudo = self.env["sale.order"].sudo()

        sale_order_sudo = SaleOrderSudo
        if CART_SESSION_CACHE_KEY in request.session:
            sale_order_sudo = SaleOrderSudo.browse(
                request.session[CART_SESSION_CACHE_KEY]
            )

            try:
                _state = sale_order_sudo and sale_order_sudo.state
            except MissingError:
                _debug.logic("cart_reset", reason="order_gone", website=self.id)
                self.sale_reset()
                sale_order_sudo = SaleOrderSudo

            if sale_order_sudo and (
                sale_order_sudo.state != "draft"
                or sale_order_sudo.get_portal_last_transaction().state
                in ("pending", "authorized", "done")
                or sale_order_sudo.website_id != self
            ):
                _debug.logic(
                    "cart_reset",
                    reason="not_a_live_draft_cart",
                    website=self.id,
                    order=sale_order_sudo.id,
                )
                self.sale_reset()
                sale_order_sudo = SaleOrderSudo

            if (
                sale_order_sudo
                and not self.env.user._is_public()
                and self.env.user.partner_id.id != sale_order_sudo.partner_id.id
                and not request.env.cr.readonly
            ):
                _debug.lifecycle(
                    "cart_partner_reassigned",
                    order=sale_order_sudo.id,
                    partner=self.env.user.partner_id.id,
                )
                sale_order_sudo._update_address(
                    self.env.user.partner_id.id, ["partner_id"]
                )
        elif (
            self.env.user
            and not self.env.user._is_public()
            and self.env.user.partner_id.filtered_domain(
                self.env["res.partner"]._check_company_domain(self.company_id.id)
            )
        ):
            partner_sudo = self.env.user.partner_id
            abandonned_cart_sudo = SaleOrderSudo.search(
                [
                    ("partner_id", "=", partner_sudo.id),
                    ("website_id", "=", self.id),
                    ("state", "=", "draft"),
                ],
                limit=1,
            )
            if abandonned_cart_sudo:
                _debug.logic(
                    "cart_resumed",
                    website=self.id,
                    order=abandonned_cart_sudo.id,
                    partner=partner_sudo.id,
                )
                if not request.env.cr.readonly:
                    abandonned_cart_sudo._update_address(
                        partner_sudo.id, ["partner_id"]
                    )
                    abandonned_cart_sudo._remove_invalid_cart_lines()
                sale_order_sudo = abandonned_cart_sudo

        if (
            sale_order_sudo or not self.env.user._is_public()
        ) and sale_order_sudo.id != request.session.get(CART_SESSION_CACHE_KEY):
            request.session[CART_SESSION_CACHE_KEY] = sale_order_sudo.id
            if "website_sale_cart_quantity" not in request.session:
                request.session["website_sale_cart_quantity"] = (
                    sale_order_sudo.cart_quantity
                )
        return sale_order_sudo

    def sale_reset(self):
        _debug.lifecycle(
            "sale_session_reset", order=request.session.get(CART_SESSION_CACHE_KEY)
        )
        request.session.pop(CART_SESSION_CACHE_KEY, None)
        request.session.pop("website_sale_cart_quantity", None)
        request.session.pop(PRICELIST_SESSION_CACHE_KEY, None)
        request.session.pop(FISCAL_POSITION_SESSION_CACHE_KEY, None)
        request.session.pop(PRICELIST_SELECTED_SESSION_CACHE_KEY, None)

    @api.model
    def action_dashboard_redirect(self):
        if self.env.user.has_group("sale.group_sale_salesman"):
            return self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
                "website.backend_dashboard"
            )
        return super().action_dashboard_redirect()

    def get_suggested_controllers(self):
        suggested_controllers = super().get_suggested_controllers()
        suggested_controllers.append(
            (_("eCommerce"), self.env["ir.http"]._url_for("/shop"), "website_sale")
        )
        return suggested_controllers

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if not self.has_ecommerce_access():
            return result
        if search_type in ["products", "product_categories_only", "all"]:
            result.append(
                self.env["product.public.category"]._search_get_detail(
                    self, order, options
                )
            )
        if search_type in ["products", "products_only", "all"]:
            result.append(
                self.env["product.template"]._search_get_detail(self, order, options)
            )
        return result

    def _get_product_page_proportions(self):
        self.check_singleton()

        return {
            "none": (0, 12),
            "50_pc": (6, 6),
            "66_pc": (8, 4),
            "100_pc": (12, 12),
        }.get(self.product_page_image_width)

    def _get_product_page_grid_image_spacing_classes(self):
        spacing_map = {
            "none": "gap-0",
            "small": "gap-1",
            "medium": "gap-2",
            "big": "gap-3",
        }
        return spacing_map.get(self.product_page_image_spacing)

    def _get_product_page_grid_image_rounded_classes(self):
        roundness_map = {
            "none": "o_wsale_product_page_opt_image_radius_none",
            "small": "o_wsale_product_page_opt_image_radius_small",
            "medium": "o_wsale_product_page_opt_image_radius_medium",
            "big": "o_wsale_product_page_opt_image_radius_big",
        }
        return roundness_map.get(self.product_page_image_roundness)

    def _get_product_page_container(self):
        return (
            self.shop_page_container
            if self.product_page_container == "unset"
            else self.product_page_container
        )

    @api.model
    def _send_abandoned_cart_email(self):
        for website in self.search([]):
            if not website.send_abandoned_cart_email:
                continue
            all_abandoned_carts = self.env["sale.order"].search(  # noqa: E8507 - one query per website
                [
                    ("is_abandoned_cart", "=", True),
                    ("cart_recovery_email_sent", "=", False),
                    ("website_id", "=", website.id),
                    (
                        "date_order",
                        ">=",
                        website.send_abandoned_cart_email_activation_time,
                    ),
                ]
            )
            if not all_abandoned_carts:
                continue

            abandoned_carts = all_abandoned_carts._filter_can_send_abandoned_cart_mail()
            _debug.pipeline(
                "abandoned_cart_mails",
                website=website.id,
                candidates=len(all_abandoned_carts),
                sendable=len(abandoned_carts),
            )
            (all_abandoned_carts - abandoned_carts).cart_recovery_email_sent = True
            for sale_order in abandoned_carts:
                template = self.env.ref("website_sale.mail_template_sale_cart_recovery")
                email_vals = (
                    {}
                    if template.email_to or template.partner_to
                    else {"email_to": sale_order.partner_id.email_formatted}
                )
                template.send_mail(sale_order.id, email_values=email_vals)
                sale_order.cart_recovery_email_sent = True

    @api.model_create_multi
    def create(self, vals_list):
        websites = super().create(vals_list)
        _debug.lifecycle("checkout_steps_created", websites=websites)
        for website in websites:
            website._create_checkout_steps()
        return websites

    def _create_checkout_steps(self):
        generic_steps = (
            self.env["website.checkout.step"]
            .sudo()
            .search(
                [
                    ("website_id", "=", False),
                ]
            )
        )
        for step in generic_steps:
            is_published = True
            if step.step_href == "/shop/extra_info":
                is_published = (
                    self.with_context(website_id=self.id)
                    .viewref("website_sale.extra_info")
                    .active
                )
            step.copy({"website_id": self.id, "is_published": is_published})

    def _get_checkout_step(self, href):
        return (
            self.env["website.checkout.step"]
            .sudo()
            .search(
                [
                    ("website_id", "=", self.id),
                    ("step_href", "=", href),
                ],
                limit=1,
            )
        )

    def _get_domain_allowed_steps(self):
        return [("website_id", "=", self.id), ("is_published", "=", True)]

    def _get_checkout_steps(self):
        return (
            self.env["website.checkout.step"]
            .sudo()
            .search(self._get_domain_allowed_steps(), order="sequence")
        )

    def _get_checkout_step_values(self):
        def rewrite(path):
            return self.env["ir.http"].url_rewrite(path)[0]

        href = rewrite(request.httprequest.path)
        if href == rewrite("/shop/address"):
            href = rewrite("/shop/checkout")

        allowed_steps_domain = self._get_domain_allowed_steps()
        current_step = request.env["website.checkout.step"].sudo()
        for step in current_step.search(allowed_steps_domain):
            if rewrite(step.step_href) == href:
                current_step = step
                href = step.step_href
                break
        next_step = current_step._get_next_checkout_step(allowed_steps_domain)
        previous_step = current_step._get_previous_checkout_step(allowed_steps_domain)

        next_href = next_step.step_href
        if next_step.step_href == "/shop/checkout":
            next_href = "/shop/checkout?try_skip_step=true"
        if request.httprequest.path == rewrite("/shop/address"):
            next_href = False

        return {
            "current_website_checkout_step_href": href,
            "previous_website_checkout_step": previous_step,
            "next_website_checkout_step": next_step,
            "next_website_checkout_step_href": next_href,
        }

    def has_ecommerce_access(self):
        return not (self.env.user._is_public() and self.ecommerce_access == "logged_in")

    def _get_canonical_url(self):
        canonical_url = urlsplit(super()._get_canonical_url())

        try:
            rule = self.env["ir.http"]._match(canonical_url.path)[0].rule
        except NotFound:
            rule = None
        if rule == (
            '/shop/<model("product.public.category"):category>/<model("product.template"):product>'
        ):
            path_parts = canonical_url.path.split("/")
            path_parts.pop(2)
            canonical_url = canonical_url._replace(path="/".join(path_parts))
        return urlunsplit(canonical_url)

    def _get_snippet_defaults(self, snippet):
        return super()._get_snippet_defaults(snippet) | const.SNIPPET_DEFAULTS.get(
            snippet, {}
        )

    def _get_product_image_ratio(self):
        classes = self.shop_opt_products_design_classes or ""
        ratio_mapping = {
            "o_wsale_products_opt_thumb_16_9": "16_9",
            "o_wsale_products_opt_thumb_4_3": "4_3",
            "o_wsale_products_opt_thumb_6_5": "6_5",
            "o_wsale_products_opt_thumb_4_5": "4_5",
            "o_wsale_products_opt_thumb_2_3": "2_3",
        }
        for class_name, ratio in ratio_mapping.items():
            if class_name in classes:
                return ratio
        return "1_1"

    def _get_product_image_ratio_height(self):
        match self._get_product_image_ratio():
            case "16_9":
                return "36px"
            case "4_3":
                return "48px"
            case "6_5":
                return "53px"
            case "4_5":
                return "96px"
        return "64px"

    def _get_domain_basic_feed_product(self):
        return Domain.AND(
            [
                Domain("is_published", "=", True),
                Domain("type", "in", ("consu", "combo")),
                self.website_domain(),
            ]
        )

    def _is_default_feed_valid(self):
        self.check_singleton()
        product_count = self.env["product.product"].search_count(
            self._get_domain_basic_feed_product(),
            limit=const.PRODUCT_FEED_SOFT_LIMIT + 1,
        )
        return product_count <= const.PRODUCT_FEED_SOFT_LIMIT

    def _create_product_feeds(self):
        self.env["product.feed"].create(
            [
                {
                    "name": website.env._("GMC 1"),
                    "website_id": website.id,
                }
                for website in self.filtered(lambda w: w._is_default_feed_valid())
            ]
        )
