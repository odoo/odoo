# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging

from werkzeug import urls
from werkzeug.exceptions import NotFound

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import AccessError

from odoo.fields import Domain
from odoo.http import request
from odoo.osv import expression
from odoo.tools import file_open, ormcache
from odoo.tools.translate import LazyTranslate, _

from odoo.addons.website_sale import const


logger = logging.getLogger(__name__)
_lt = LazyTranslate(__name__)


CART_SESSION_CACHE_KEY = 'sale_order_id'
FISCAL_POSITION_SESSION_CACHE_KEY = 'fiscal_position_id'
PRICELIST_SESSION_CACHE_KEY = 'website_sale_current_pl'
PRICELIST_SELECTED_SESSION_CACHE_KEY = 'website_sale_selected_pl_id'


class Website(models.Model):
    _inherit = 'website'

    #=== DEFAULT METHODS ===#

    def _default_salesteam_id(self):
        team = self.env.ref('sales_team.salesteam_website_sales', raise_if_not_found=False)
        if team and team.active:
            return team.id
        return None

    def _default_recovery_mail_template(self):
        try:
            return self.env.ref('website_sale.mail_template_sale_cart_recovery').id
        except ValueError:
            return False

    #=== FIELDS ===#

    enabled_portal_reorder_button = fields.Boolean(string="Re-order From Portal")
    salesperson_id = fields.Many2one(
        string="Salesperson",
        comodel_name='res.users',
        domain=[('share', '=', False)],
    )
    salesteam_id = fields.Many2one(
        string="Sales Team",
        comodel_name='crm.team',
        index='btree_not_null',
        ondelete='set null',
        default=_default_salesteam_id,
    )
    show_line_subtotals_tax_selection = fields.Selection(
        string="Line Subtotals Tax Display",
        selection=[
            ('tax_excluded', "Tax Excluded"),
            ('tax_included', "Tax Included"),
        ],
        compute='_compute_show_line_subtotals_tax_selection',
        readonly=False,
        store=True,
    )

    add_to_cart_action = fields.Selection(
        selection=[
            ('stay', "Stay on Product Page"),
            ('go_to_cart', "Go to cart"),
            ('force_dialog', "Let the user decide (dialog)"),
        ],
        default='stay',
    )
    auth_signup_uninvited = fields.Selection(default='b2c')
    account_on_checkout = fields.Selection(
        string="Customer Accounts",
        selection=[
            ('optional', "Optional"),
            ('disabled', "Disabled (buy as guest)"),
            ('mandatory', "Mandatory (no guest checkout)"),
        ],
        default='optional',
    )
    cart_recovery_mail_template_id = fields.Many2one(
        string="Cart Recovery Email",
        comodel_name='mail.template',
        domain=[('model', '=', 'sale.order')],
        default=_default_recovery_mail_template,
    )
    contact_us_button_url = fields.Char(
        string="Contact Us Button URL", translate=True, default="/contactus",
    )
    cart_abandoned_delay = fields.Float(string="Abandoned Delay", default=10.0)
    send_abandoned_cart_email = fields.Boolean(
        string="Send email to customers who abandoned their cart.",
    )
    send_abandoned_cart_email_activation_time = fields.Datetime(
        string="Time when the 'Send abandoned cart email' feature was activated.",
        compute='_compute_send_abandoned_cart_email_activation_time',
        store=True,
    )
    shop_ppg = fields.Integer(
        string="Number of products in the grid on the shop", default=20,
    )
    shop_ppr = fields.Integer(string="Number of grid columns on the shop", default=4)

    shop_gap = fields.Char(string="Grid-gap on the shop", default="16px", required=False)

    shop_default_sort = fields.Selection(
        selection='_get_product_sort_mapping', required=True, default='website_sequence asc')

    shop_extra_field_ids = fields.One2many(
        string="E-Commerce Extra Fields",
        comodel_name='website.sale.extra.field',
        inverse_name='website_id',
    )

    product_page_image_layout = fields.Selection(
        selection=[
            ('carousel', "Carousel"),
            ('grid', "Grid"),
        ],
        required=True,
        default='carousel',
    )
    product_page_image_width = fields.Selection(
        selection=[
            ('none', "Hidden"),
            ('50_pc', "50 %"),
            ('66_pc', "66 %"),
            ('100_pc', "100 %"),
        ],
        required=True,
        default='50_pc',
    )
    product_page_image_spacing = fields.Selection(
        selection=[
            ('none', "None"),
            ('small', "Small"),
            ('medium', "Medium"),
            ('big', "Big"),
        ],
        required=True,
        default='small',
    )
    ecommerce_access = fields.Selection(
        selection=[
            ('everyone', "All users"),
            ('logged_in', "Logged in users"),
        ],
        required=True,
        default='everyone',
    )
    product_page_grid_columns = fields.Integer(default=2)

    prevent_zero_price_sale = fields.Boolean(string="Hide 'Add To Cart' when price = 0")

    enabled_gmc_src = fields.Boolean(string="Google Merchant Center Data Source")

    currency_id = fields.Many2one(
        string="Default Currency",
        comodel_name='res.currency',
        compute='_compute_currency_id',
    )
    pricelist_ids = fields.One2many(
        string="Price list available for this Ecommerce/Website",
        comodel_name='product.pricelist',
        compute="_compute_pricelist_ids",
    )

    _check_gmc_ecommerce_access = models.Constraint(
        'CHECK (NOT enabled_gmc_src OR ecommerce_access = \'everyone\')',
        "eCommerce must be accessible to all users for Google Merchant Center to operate properly.",
    )

    #=== COMPUTE METHODS ===#

    def _compute_pricelist_ids(self):
        for website in self:
            website = website.with_company(website.company_id)
            ProductPricelist = website.env['product.pricelist']  # with correct company in env
            website.pricelist_ids = ProductPricelist.sudo().search(
                ProductPricelist._get_website_pricelists_domain(website)
            )

    @api.depends('company_id')
    def _compute_currency_id(self):
        for website in self:
            website.currency_id = (
                request and request.pricelist.currency_id or website.company_id.sudo().currency_id
            )

    @api.depends('send_abandoned_cart_email')
    def _compute_send_abandoned_cart_email_activation_time(self):
        for website in self:
            if website.send_abandoned_cart_email:
                website.send_abandoned_cart_email_activation_time = fields.Datetime.now()

    @api.depends('company_id.account_fiscal_country_id')
    def _compute_show_line_subtotals_tax_selection(self):
        for website in self:
            website.show_line_subtotals_tax_selection = 'tax_excluded'

    #=== SELECTION METHODS ===#

    @staticmethod
    def _get_product_sort_mapping():
        return [
            ('website_sequence asc', _("Featured")),
            ('publish_date desc', _("Newest Arrivals")),
            ('name asc', _("Name (A-Z)")),
            ('list_price asc', _("Price - Low to High")),
            ('list_price desc', _("Price - High to Low")),
        ]

    #=== BUSINESS METHODS ===#

    @api.model
    def get_configurator_shop_page_styles(self):
        """Format and return the ids and images of each shop page style for website onboarding.

        :return: The shop page style information.
        :rtype: list[dict]
        """
        return [
            {'option': option, 'img_src': config['img_src'], 'title': config['title']}
            for option, config in const.SHOP_PAGE_STYLE_MAPPING.items()
        ]

    @api.model
    def get_configurator_product_page_styles(self):
        """Format and return ids and images of each product page style for website onboarding.

        :return: The product page style information.
        :rtype: list[dict]
        """
        return [
            {'option': option, 'img_src': config['img_src'], 'title': config['title']}
            for option, config in const.PRODUCT_PAGE_STYLE_MAPPING.items()
        ]

    @api.model
    def configurator_apply(
        self, *, shop_page_style_option=None, product_page_style_option=None, **kwargs
    ):
        """Override of `website` to apply eCommerce page style configurations.

        :param str shop_page_style_option: The key of the selected shop page style option. See
                                           `const.SHOP_PAGE_STYLE_MAPPING`.
        :param str product_page_style_option: The key of the selected product page style option. See
                                              `const.PRODUCT_PAGE_STYLE_MAPPING`.
        """
        res = super().configurator_apply(**kwargs)

        website = self.get_current_website()
        website_settings = {}
        views_to_disable = []
        views_to_enable = []
        ThemeUtils = self.env['theme.utils'].with_context(website_id=website.id)

        def parse_style_config(style_config_):
            website_settings.update(style_config_['website_fields'])
            views_to_disable.extend(style_config_['views']['disable'])
            views_to_enable.extend(style_config_['views']['enable'])

        # Extract shop page settings.
        if shop_page_style_option:
            style_config = const.SHOP_PAGE_STYLE_MAPPING[shop_page_style_option]
            parse_style_config(style_config)

        # Extract product page settings.
        if product_page_style_option:
            style_config = const.PRODUCT_PAGE_STYLE_MAPPING[product_page_style_option]
            parse_style_config(style_config)

        # Apply eCommerce page style configurations.
        if website_settings:
            website.write(website_settings)
        for xml_id in views_to_disable:
            if (
                xml_id == 'website_sale_comparison.product_add_to_compare'
                and 'website_sale_comparison' not in self.env['ir.module.module']._installed()
            ):
                continue
            ThemeUtils.disable_view(xml_id)
        for xml_id in views_to_enable:
            ThemeUtils.enable_view(xml_id)

        return res

    def configurator_addons_apply(self, industry_name=None, **kwargs):
        """Override of `website` to generate eCommerce categories for a given industry using AI."""

        def generate_categories(industry_name_):
            lang = self.env.context.get('lang')
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
                f']}}\n'
                f"Constraints:\n"
                f"Language: {lang}\n"
                f"Category Names: Must be nouns only (no adjectives).\n"
                f"Description Length: Keep descriptions very short and to the point (ideally under 20 words).\n"
                f"Persuasion: Descriptions should be persuasive and designed to attract attention.\n"
                f"Number of Categories: Exactly 8 categories are required.\n"
                f"Now, generate the 8 eCommerce categories for the {industry_name_}, adhering to the specified format and constraints."
            )
            IrConfigParameterSudo = self.env['ir.config_parameter'].sudo()
            database_id = IrConfigParameterSudo.get_param('database.uuid')
            try:
                response = self._OLG_api_rpc('/api/olg/1/chat', {
                    'prompt': prompt,
                    'conversation_history': [],
                    'database_id': database_id,
                })
            except AccessError:
                logger.warning("API is unreachable for the category generation")
                return None

            if response['status'] == 'success':
                content = response['content'].replace('```json\n', '').replace('\n```', '')
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.warning("API response is not a valid JSON for the category generation")
            elif response['status'] == 'error_prompt_too_long':
                logger.warning("Prompt is too long for the category generation")
            elif response['status'] == 'limit_call_reached':
                logger.warning("Limit call reached for the category generation")
            else:
                logger.warning("Response could not be generated for the category generation")
            return None

        res = super().configurator_addons_apply(industry_name=industry_name, **kwargs)

        if self.env['product.public.category'].search_count([], limit=1):
            logger.info("Categories already exist, skipping AI generation.")
            return

        category_specs = generate_categories(industry_name)
        if not isinstance(category_specs, dict):
            return

        if len(category_specs.get('categories')) == 8:
            images_names = [f'shape_mixed_{i}.png' for i in range(1, 9)]
            categories = []
            for idx, cat in enumerate(category_specs['categories']):
                image_name = images_names[idx]
                img_path = 'website_sale/static/src/img/categories/' + image_name
                with file_open(img_path, 'rb') as file:
                    image_base64 = base64.b64encode(file.read())
                categories.append({
                    'name': cat['name'],
                    'website_description': cat['description'],
                    'image_1920': image_base64,
                })
            self.env['product.public.category'].sudo().create(categories)
        return res

    # This method is cached, must not return records! See also #8795
    @ormcache(
        'country_code', 'show_visible', 'current_pl_id', 'website_pricelist_ids', 'partner_pl_id',
    )
    def _get_pl_partner_order(
        self, country_code, show_visible, current_pl_id, website_pricelist_ids, partner_pl_id=False
    ):
        """ Return the list of pricelists that can be used on website for the current user.

        :param str country_code: code iso or False, If set, we search only price list available for this country
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
        :param int current_pl_id: The current pricelist used on the website
            (If not selectable but currently used anyway, e.g. pricelist with promo code)
        :param tuple website_pricelist_ids: List of ids of pricelists available for this website
        :param int partner_pl_id: the partner pricelist
        :returns: list of product.pricelist ids
        :rtype: list
        """
        self.ensure_one()
        pricelists = self.env['product.pricelist']

        def check_pricelist(pricelist):
            if show_visible:
                return pricelist.selectable or pricelist.id == current_pl_id
            else:
                return True

        # Note: 1. pricelists from all_pl are already website compliant (went through
        #          `_get_website_pricelists_domain`)
        #       2. do not read `property_product_pricelist` here as `_get_pl_partner_order`
        #          is cached and the result of this method will be impacted by that field value.
        #          Pass it through `partner_pl_id` parameter instead to invalidate the cache.

        # If there is a GeoIP country, find a pricelist for it
        if country_code:
            pricelists |= self.env['res.country.group'].search(
                [('country_ids.code', '=', country_code)]
            ).pricelist_ids.filtered(
                lambda pl: pl._is_available_on_website(self) and check_pricelist(pl)
            )

        # no GeoIP or no pricelist for this country
        if not pricelists:
            pricelists = pricelists.browse(website_pricelist_ids).filtered(
                lambda pl: check_pricelist(pl) and not (country_code and pl.country_group_ids))

        # if logged in, add partner pl (which is `property_product_pricelist`, might not be website compliant)
        if not self.env.user._is_public():
            # keep partner_pricelist only if website compliant
            partner_pricelist = pricelists.browse(partner_pl_id).filtered(
                lambda pl:
                    pl._is_available_on_website(self)
                    and check_pricelist(pl)
                    and pl._is_available_in_country(country_code)
            )
            pricelists |= partner_pricelist

        # This method is cached, must not return records! See also #8795
        # sudo is needed to ensure no records rules are applied during the sorted call,
        # we only want to reorder the records on hand, not filter them.
        return pricelists.sudo().sorted().ids

    def get_pricelist_available(self, show_visible=False):
        """ Return the list of pricelists that can be used on website for the current user.
        Country restrictions will be detected with GeoIP (if installed).
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
        :returns: pricelist recordset
        """
        self.ensure_one()

        ProductPricelist = self.env['product.pricelist']

        if not self.env['res.groups']._is_feature_enabled('product.group_product_pricelist'):
            return ProductPricelist  # Skip pricelist computation if pricelists are disabled.

        country_code = self._get_geoip_country_code()
        website = self.with_company(self.company_id)

        partner_sudo = website.env.user.partner_id
        is_user_public = self.env.user._is_public()
        if not is_user_public:
            # Don't needlessly trigger `depends_context` recompute
            ctx = {'country_code': country_code} if country_code else {}
            partner_pricelist_id = partner_sudo.with_context(**ctx).property_product_pricelist.id
        else:  # public user: do not compute partner pl (not used)
            partner_pricelist_id = False
        website_pricelists = website.sudo().pricelist_ids

        current_pricelist_id = request and request.session.get(PRICELIST_SESSION_CACHE_KEY) or None

        pricelist_ids = website._get_pl_partner_order(
            country_code,
            show_visible,
            current_pl_id=current_pricelist_id,
            website_pricelist_ids=tuple(website_pricelists.ids),
            partner_pl_id=partner_pricelist_id,
        )

        return ProductPricelist.browse(pricelist_ids)

    def is_pricelist_available(self, pl_id):
        """ Return a boolean to specify if a specific pricelist can be manually set on the website.
        Warning: It check only if pricelist is in the 'selectable' pricelists or the current pricelist.
        :param int pl_id: The pricelist id to check
        :returns: Boolean, True if valid / available
        """
        return pl_id in self.get_pricelist_available(show_visible=False).ids

    def _get_geoip_country_code(self):
        return request and request.geoip.country_code or False

    def sale_product_domain(self):
        website_domain = self.get_current_website().website_domain()
        if not self.env.user._is_internal():
            website_domain = expression.AND([website_domain, [
                ('is_published', '=', True),
                ('service_tracking', 'in', self.env['product.template']._get_saleable_tracking_types()),
            ]])
        return expression.AND([self._product_domain(), website_domain])

    def _product_domain(self):
        return [('sale_ok', '=', True)]

    def _create_cart(self):
        self.ensure_one()

        partner_sudo = self.env.user.partner_id

        so_data = self._prepare_sale_order_values(partner_sudo)
        sale_order_sudo = self.env['sale.order'].with_user(
            SUPERUSER_ID
        ).with_company(self.company_id).create(so_data)

        # The order was created with SUPERUSER_ID, revert back to request user.
        sale_order_sudo = sale_order_sudo.with_user(self.env.user).sudo()

        request.session[CART_SESSION_CACHE_KEY] = sale_order_sudo.id
        request.session['website_sale_cart_quantity'] = sale_order_sudo.cart_quantity
        request.cart = sale_order_sudo

        return sale_order_sudo

    def _prepare_sale_order_values(self, partner_sudo):
        self.ensure_one()

        return {
            'company_id': self.company_id.id,
            'partner_id': partner_sudo.id,

            'fiscal_position_id': request.fiscal_position.id,
            'pricelist_id': request.pricelist.id,

            'team_id': self.salesteam_id.id,
            'website_id': self.id,
        }

    def _get_and_cache_current_pricelist(self):
        """Retrieve and cache the current pricelist for the session.

        Note: self.ensure_one()

        :return: The determined pricelist, which could be empty, as a sudoed record.
        :rtype: product.pricelist
        """
        self.ensure_one()

        ProductPricelistSudo = self.env['product.pricelist'].sudo()
        if not self.env['res.groups']._is_feature_enabled('product.group_product_pricelist'):
            return ProductPricelistSudo  # Skip pricelist computation if pricelists are disabled.

        if PRICELIST_SESSION_CACHE_KEY in request.session:
            pricelist_sudo = ProductPricelistSudo.browse(
                request.session[PRICELIST_SESSION_CACHE_KEY]
            )
            if pricelist_sudo and (
                pricelist_sudo.exists()
                and pricelist_sudo._is_available_on_website(self)
                and pricelist_sudo._is_available_in_country(self._get_geoip_country_code())
            ):
                return pricelist_sudo.sudo()

        if cart_sudo := request.cart:
            if not request.env.cr.readonly:
                # If there is a cart, recompute on the cart and take it from there
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
        """Retrieve and cache the current fiscal position for the session.

        Note: self.ensure_one()

        :return: A sudoed fiscal position record.
        :rtype: account.fiscal.position
        """
        self.ensure_one()

        AccountFiscalPositionSudo = self.env['account.fiscal.position'].sudo()
        fpos_sudo = AccountFiscalPositionSudo

        if FISCAL_POSITION_SESSION_CACHE_KEY in request.session:
            fpos_sudo = AccountFiscalPositionSudo.browse(
                request.session[FISCAL_POSITION_SESSION_CACHE_KEY]
            )
            if fpos_sudo and fpos_sudo.exists():
                return fpos_sudo

        partner_sudo = self.env.user.partner_id

        # If the current user is the website public user, the fiscal position
        # is computed according to geolocation.
        if request and request.geoip.country_code and self.partner_id.id == partner_sudo.id:
            country = self.env['res.country'].search(
                [('code', '=', request.geoip.country_code)],
                limit=1,
            )
            partner_geoip = self.env['res.partner'].new({'country_id': country.id})
            fpos_sudo = AccountFiscalPositionSudo._get_fiscal_position(partner_geoip)

        if not fpos_sudo:
            fpos_sudo = AccountFiscalPositionSudo._get_fiscal_position(partner_sudo)

        request.session[FISCAL_POSITION_SESSION_CACHE_KEY] = fpos_sudo.id

        return fpos_sudo

    def _get_and_cache_current_cart(self):
        """ Retrieves and caches the current cart for the session.

        Note: self.ensure_one()

        :return: A sudoed Sales order record.
        :rtype: sale.order
        """
        self.ensure_one()

        SaleOrderSudo = self.env['sale.order'].sudo()

        sale_order_sudo = SaleOrderSudo
        partner_sudo = self.env.user.partner_id
        if CART_SESSION_CACHE_KEY in request.session:
            sale_order_sudo = SaleOrderSudo.browse(request.session[CART_SESSION_CACHE_KEY])
            if sale_order_sudo and (
                not sale_order_sudo.exists()
                or sale_order_sudo.state != 'draft'
                or sale_order_sudo.get_portal_last_transaction().state in (
                    'pending', 'authorized', 'done'
                )
                or sale_order_sudo.website_id != self
            ):
                self.sale_reset()
                sale_order_sudo = SaleOrderSudo

            # If customer logs in, the cart must be recomputed based on his information (in the
            # first non readonly request).
            if (
                sale_order_sudo
                and not self.env.user._is_public()
                and partner_sudo.id != sale_order_sudo.partner_id.id
                and not request.env.cr.readonly
            ):
                sale_order_sudo._update_address(partner_sudo.id, ['partner_id'])
        elif (
            self.env.user
            and not self.env.user._is_public()
            # If the company of the partner doesn't allow them to buy from this website, updating
            # the cart customer would raise because of multi-company checks.
            # No abandoned cart should be returned in this situation.
            and partner_sudo.filtered_domain(
                self.env['res.partner']._check_company_domain(self.company_id.id)
            )
        ):  # Search for abandonned cart.
            abandonned_cart_sudo = SaleOrderSudo.search([
                ('partner_id', '=', partner_sudo.id),
                ('website_id', '=', self.id),
                ('state', '=', 'draft'),
            ], limit=1)
            if abandonned_cart_sudo:
                if not request.env.cr.readonly:
                    # Force the recomputation of the pricelist and fiscal position when resurrecting
                    # an abandonned cart
                    abandonned_cart_sudo._update_address(partner_sudo.id, ['partner_id'])
                    abandonned_cart_sudo._verify_cart()
                sale_order_sudo = abandonned_cart_sudo

        if (
            (sale_order_sudo or not self.env.user._is_public())
            and sale_order_sudo.id != request.session.get(CART_SESSION_CACHE_KEY)
        ):
            # Store the id of the cart if there is one, or False if the user is logged in, to avoid
            # searching for an abandoned cart again for that user.
            request.session[CART_SESSION_CACHE_KEY] = sale_order_sudo.id
            if 'website_sale_cart_quantity' not in request.session:
                request.session['website_sale_cart_quantity'] = sale_order_sudo.cart_quantity
        return sale_order_sudo

    def sale_reset(self):
        request.session.pop(CART_SESSION_CACHE_KEY, None)
        request.session.pop('website_sale_cart_quantity', None)
        request.session.pop(PRICELIST_SESSION_CACHE_KEY, None)
        request.session.pop(FISCAL_POSITION_SESSION_CACHE_KEY, None)
        request.session.pop(PRICELIST_SELECTED_SESSION_CACHE_KEY, None)

    @api.model
    def action_dashboard_redirect(self):
        if self.env.user.has_group('sales_team.group_sale_salesman'):
            return self.env['ir.actions.actions']._for_xml_id('website.backend_dashboard')
        return super().action_dashboard_redirect()

    def get_suggested_controllers(self):
        suggested_controllers = super().get_suggested_controllers()
        suggested_controllers.append((_('eCommerce'), self.env['ir.http']._url_for('/shop'), 'website_sale'))
        return suggested_controllers

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if not self.has_ecommerce_access():
            return result
        if search_type in ['products', 'product_categories_only', 'all']:
            result.append(self.env['product.public.category']._search_get_detail(self, order, options))
        if search_type in ['products', 'products_only', 'all']:
            result.append(self.env['product.template']._search_get_detail(self, order, options))
        return result

    def _get_product_page_proportions(self):
        """
        Returns the number of columns (css) that both the images and the product details should take.
        """
        self.ensure_one()

        return {
            'none': (0, 12),
            '50_pc': (6, 6),
            '66_pc': (8, 4),
            '100_pc': (12, 12),
        }.get(self.product_page_image_width)

    def _get_product_page_grid_image_spacing_classes(self):
        spacing_map = {
            'none': 'm-0',
            'small': 'm-1',
            'medium': 'm-2',
            'big': 'm-3',
        }
        return spacing_map.get(self.product_page_image_spacing)

    @api.model
    def _send_abandoned_cart_email(self):
        for website in self.search([]):
            if not website.send_abandoned_cart_email:
                continue
            all_abandoned_carts = self.env['sale.order'].search([
                ('is_abandoned_cart', '=', True),
                ('cart_recovery_email_sent', '=', False),
                ('website_id', '=', website.id),
                ('date_order', '>=', website.send_abandoned_cart_email_activation_time),
            ])
            if not all_abandoned_carts:
                continue

            abandoned_carts = all_abandoned_carts._filter_can_send_abandoned_cart_mail()
            # Mark abandoned carts that failed the filter as sent to avoid rechecking them again and again.
            (all_abandoned_carts - abandoned_carts).cart_recovery_email_sent = True
            for sale_order in abandoned_carts:
                template = self.env.ref('website_sale.mail_template_sale_cart_recovery')
                # fallback email_vals in case partner_to and email_to were emptied
                email_vals = {} if template.email_to or template.partner_to else {
                    'email_to': sale_order.partner_id.email_formatted
                }
                template.send_mail(sale_order.id, email_values=email_vals)
                sale_order.cart_recovery_email_sent = True

    @api.model_create_multi
    def create(self, vals_list):
        websites = super().create(vals_list)
        for website in websites:
            website._create_checkout_steps()
        return websites

    def _create_checkout_steps(self):
        generic_steps = self.env['website.checkout.step'].sudo().search([
            ('website_id', '=', False),
        ])
        for step in generic_steps:
            is_published = True
            if step.step_href == '/shop/extra_info':
                is_published = self.with_context(website_id=self.id).viewref('website_sale.extra_info').active
            step.copy({'website_id': self.id, 'is_published': is_published})

    def _get_checkout_step(self, href):
        return self.env['website.checkout.step'].sudo().search([
            ('website_id', '=', self.id),
            ('step_href', '=', href),
        ], limit=1)

    def _get_allowed_steps_domain(self):
        return [
            ('website_id', '=', self.id),
            ('is_published', '=', True)
        ]

    def _get_checkout_steps(self):
        steps = self.env['website.checkout.step'].sudo().search(
            self._get_allowed_steps_domain(), order='sequence'
        )
        return steps

    def _get_checkout_step_values(self, href=None):
        href = href or request.httprequest.path
        # /shop/address is associated with the delivery step
        if href == '/shop/address':
            href = '/shop/checkout'

        allowed_steps_domain = self._get_allowed_steps_domain()
        current_step = request.env['website.checkout.step'].sudo().search(
            Domain.AND([allowed_steps_domain, [('step_href', '=', href)]]), limit=1
        )
        next_step = current_step._get_next_checkout_step(allowed_steps_domain)
        previous_step = current_step._get_previous_checkout_step(allowed_steps_domain)

        next_href = next_step.step_href
        # try_skip_step option required on /shop/checkout next button
        if next_step.step_href == '/shop/checkout':
            next_href = '/shop/checkout?try_skip_step=true'
        # redirect handled by '/shop/address/submit' route when all values are properly filled
        if request.httprequest.path == '/shop/address':
            next_href = False

        return {
            'current_website_checkout_step_href': href,
            'previous_website_checkout_step': previous_step,
            'next_website_checkout_step': next_step,
            'next_website_checkout_step_href': next_href,
        }

    def has_ecommerce_access(self):
        """ Return whether the current user is allowed to access eCommerce-related content. """
        return not (self.env.user._is_public() and self.ecommerce_access == 'logged_in')

    def _get_canonical_url(self):
        """ Override of `website` to customize the canonical URL for product pages.

        A product page URL can have a category in its path. However, since the page is exactly the
        same whether the category is present or not, the canonical URL shouldn't include the
        category.
        """
        canonical_url = urls.url_parse(super()._get_canonical_url())

        try:
            rule = self.env['ir.http']._match(canonical_url.path)[0].rule
        except NotFound:
            rule = None
        if rule == (
            '/shop/<model("product.public.category"):category>/<model("product.template"):product>'
        ):
            path_parts = canonical_url.path.split('/')
            path_parts.pop(2)
            canonical_url = canonical_url.replace(path='/'.join(path_parts))
        return canonical_url.to_url()
