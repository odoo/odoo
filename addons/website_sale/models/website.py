# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, _, _lt, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.http import request
from odoo.osv import expression

from odoo.addons.http_routing.models.ir_http import url_for


class Website(models.Model):
    _inherit = 'website'

    def _default_salesteam_id(self):
        team = self.env.ref('sales_team.salesteam_website_sales', False)
        if team and team.active:
            return team.id
        else:
            return None

    salesperson_id = fields.Many2one('res.users', string='Salesperson')
    salesteam_id = fields.Many2one('crm.team',
        string='Sales Team', ondelete="set null",
        default=_default_salesteam_id)
    show_line_subtotals_tax_selection = fields.Selection(
        selection=[
            ('tax_excluded', "Tax Excluded"),
            ('tax_included', "Tax Included"),
        ],
        string="Line Subtotals Tax Display",
        required=True, default='tax_excluded',
    )

    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', compute='_compute_fiscal_position_id')
    pricelist_id = fields.Many2one(
        'product.pricelist', compute='_compute_pricelist_id', string="Default Pricelist if any")
    currency_id = fields.Many2one(
        'res.currency', compute='_compute_currency_id', string="Default Currency")
    pricelist_ids = fields.One2many('product.pricelist', compute="_compute_pricelist_ids",
                                    string='Price list available for this Ecommerce/Website')
    # Technical: Used to recompute pricelist_ids
    all_pricelist_ids = fields.One2many('product.pricelist', 'website_id', string='All pricelists')

    def _default_recovery_mail_template(self):
        try:
            return self.env.ref('website_sale.mail_template_sale_cart_recovery').id
        except ValueError:
            return False

    cart_recovery_mail_template_id = fields.Many2one('mail.template', string='Cart Recovery Email', default=_default_recovery_mail_template, domain="[('model', '=', 'sale.order')]")
    cart_abandoned_delay = fields.Float(string="Abandoned Delay", default=10.0)
    send_abandoned_cart_email = fields.Boolean(string="Send email to customers who abandoned their cart.")

    shop_ppg = fields.Integer(default=20, string="Number of products in the grid on the shop")
    shop_ppr = fields.Integer(default=4, string="Number of grid columns on the shop")

    @staticmethod
    def _get_product_sort_mapping():
        return [
            ('website_sequence asc', _('Featured')),
            ('create_date desc', _('Newest Arrivals')),
            ('name asc', _('Name (A-Z)')),
            ('list_price asc', _('Price - Low to High')),
            ('list_price desc', _('Price - High to Low')),
        ]
    shop_default_sort = fields.Selection(selection='_get_product_sort_mapping', default='website_sequence asc', required=True)

    shop_extra_field_ids = fields.One2many('website.sale.extra.field', 'website_id', string='E-Commerce Extra Fields')

    add_to_cart_action = fields.Selection(
        selection=[
            ('stay', 'Stay on Product Page'),
            ('go_to_cart', 'Go to cart'),
        ],
        default='stay')
    auth_signup_uninvited = fields.Selection(default='b2c')
    account_on_checkout = fields.Selection(
        string="Customer Accounts",
        selection=[
            ('optional', 'Optional'),
            ('disabled', 'Disabled (buy as guest)'),
            ('mandatory', 'Mandatory (no guest checkout)'),
        ],
        default='optional')

    product_page_image_layout = fields.Selection([
        ('carousel', 'Carousel'),
        ('grid', 'Grid'),
        ], default='carousel', required=True,
    )
    product_page_grid_columns = fields.Integer(default=2)
    product_page_image_width = fields.Selection([
        ('none', 'Hidden'),
        ('50_pc', '50 %'),
        ('66_pc', '66 %'),
        ('100_pc', '100 %'),
        ], default='50_pc', required=True,
    )
    product_page_image_spacing = fields.Selection([
        ('none', 'None'),
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('big', 'Big'),
        ], default='small', required=True,
    )

    prevent_zero_price_sale = fields.Boolean(string="Hide 'Add To Cart' when price = 0")
    prevent_zero_price_sale_text = fields.Char(string="Text to show instead of price", translate=True,
                                               default="Not Available For Sale")
    contact_us_button_url = fields.Char(string="Contact Us Button URL", translate=True, default="/contactus")
    enabled_portal_reorder_button = fields.Boolean(string="Re-order From Portal")
    enabled_delivery = fields.Boolean(string="Enable Shipping", compute='_compute_enabled_delivery')

    @api.depends('all_pricelist_ids')
    def _compute_pricelist_ids(self):
        for website in self:
            website = website.with_company(website.company_id)
            ProductPricelist = website.env['product.pricelist']  # with correct company in env
            website.pricelist_ids = ProductPricelist.sudo().search(
                ProductPricelist._get_website_pricelists_domain(website)
            )

    def _compute_pricelist_id(self):
        for website in self:
            website.pricelist_id = website._get_current_pricelist()

    def _compute_fiscal_position_id(self):
        for website in self:
            website.fiscal_position_id = website._get_current_fiscal_position()

    @api.depends('all_pricelist_ids', 'pricelist_id', 'company_id')
    def _compute_currency_id(self):
        for website in self:
            website.currency_id = website.pricelist_id.currency_id or website.company_id.currency_id

    def _compute_enabled_delivery(self):
        for website in self:
            website.enabled_delivery = bool(website.env['delivery.carrier'].sudo().search_count(
                [('website_id', 'in', (False, website.id)), ('is_published', '=', True)], limit=1
            ))

    # This method is cached, must not return records! See also #8795
    @tools.ormcache(
        'country_code', 'show_visible',
        'current_pl_id', 'website_pricelist_ids',
        'partner_pl_id', 'order_pl_id',
    )
    def _get_pl_partner_order(
        self, country_code, show_visible, current_pl_id, website_pricelist_ids,
        partner_pl_id=False, order_pl_id=False
    ):
        """ Return the list of pricelists that can be used on website for the current user.

        :param str country_code: code iso or False, If set, we search only price list available for this country
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
        :param int current_pl_id: The current pricelist used on the website
            (If not selectable but currently used anyway, e.g. pricelist with promo code)
        :param tuple website_pricelist_ids: List of ids of pricelists available for this website
        :param int partner_pl_id: the partner pricelist
        :param int order_pl_id: the current cart pricelist
        :returns: list of product.pricelist ids
        :rtype: list
        """
        self.ensure_one()
        pricelists = self.env['product.pricelist']

        if show_visible:
            # Only show selectable or currently used pricelist (cart or session)
            check_pricelist = lambda pl: pl.selectable or pl.id in (current_pl_id, order_pl_id)
        else:
            check_pricelist = lambda _pl: True

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
            pricelists = pricelists.browse(website_pricelist_ids).filtered(check_pricelist)

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
        return pricelists.ids

    def get_pricelist_available(self, show_visible=False):
        """ Return the list of pricelists that can be used on website for the current user.
        Country restrictions will be detected with GeoIP (if installed).
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
        :returns: pricelist recordset
        """
        self.ensure_one()

        country_code = self._get_geoip_country_code()
        website = self.with_company(self.company_id)

        partner_sudo = website.env.user.partner_id
        is_user_public = self.env.user._is_public()
        if not is_user_public:
            last_order_pricelist = partner_sudo.last_website_so_id.pricelist_id
            partner_pricelist = partner_sudo.property_product_pricelist
        else:  # public user: do not compute partner pl (not used)
            last_order_pricelist = self.env['product.pricelist']
            partner_pricelist = self.env['product.pricelist']
        website_pricelists = website.sudo().pricelist_ids

        current_pricelist_id = self._get_cached_pricelist_id()

        pricelist_ids = website._get_pl_partner_order(
            country_code,
            show_visible,
            current_pl_id=current_pricelist_id,
            website_pricelist_ids=tuple(website_pricelists.ids),
            partner_pl_id=partner_pricelist.id,
            order_pl_id=last_order_pricelist.id)

        return self.env['product.pricelist'].browse(pricelist_ids)

    def is_pricelist_available(self, pl_id):
        """ Return a boolean to specify if a specific pricelist can be manually set on the website.
        Warning: It check only if pricelist is in the 'selectable' pricelists or the current pricelist.
        :param int pl_id: The pricelist id to check
        :returns: Boolean, True if valid / available
        """
        return pl_id in self.get_pricelist_available(show_visible=False).ids

    def _get_geoip_country_code(self):
        return request and request.geoip.country_code or False

    def _get_cached_pricelist_id(self):
        return request and request.session.get('website_sale_current_pl') or None

    def _get_current_pricelist(self):
        """
        :returns: The current pricelist record
        """
        self = self.with_company(self.company_id)
        ProductPricelist = self.env['product.pricelist']

        pricelist = ProductPricelist
        if request and request.session.get('website_sale_current_pl'):
            # `website_sale_current_pl` is set only if the user specifically chose it:
            #  - Either, he chose it from the pricelist selection
            #  - Either, he entered a coupon code
            pricelist = ProductPricelist.browse(request.session['website_sale_current_pl']).exists().sudo()
            country_code = self._get_geoip_country_code()
            if not pricelist or not pricelist._is_available_on_website(self) or not pricelist._is_available_in_country(country_code):
                request.session.pop('website_sale_current_pl')
                pricelist = ProductPricelist

        if not pricelist:
            partner_sudo = self.env.user.partner_id

            # If the user has a saved cart, it take the pricelist of this last unconfirmed cart
            pricelist = partner_sudo.last_website_so_id.pricelist_id
            if not pricelist:
                # The pricelist of the user set on its partner form.
                # If the user is not signed in, it's the public user pricelist
                pricelist = partner_sudo.property_product_pricelist

            # The list of available pricelists for this user.
            # If the user is signed in, and has a pricelist set different than the public user pricelist
            # then this pricelist will always be considered as available
            available_pricelists = self.get_pricelist_available()
            if available_pricelists and pricelist not in available_pricelists:
                # If there is at least one pricelist in the available pricelists
                # and the chosen pricelist is not within them
                # it then choose the first available pricelist.
                # This can only happen when the pricelist is the public user pricelist and this pricelist is not in the available pricelist for this localization
                # If the user is signed in, and has a special pricelist (different than the public user pricelist),
                # then this special pricelist is amongs these available pricelists, and therefore it won't fall in this case.
                pricelist = available_pricelists[0]

        return pricelist

    def sale_product_domain(self):
        website_domain = self.get_current_website().website_domain()
        if not self.env.user._is_internal():
            website_domain = expression.AND([website_domain, [('is_published', '=', True)]])
        return expression.AND([self._product_domain(), website_domain])

    def _product_domain(self):
        return [('sale_ok', '=', True)]

    def sale_get_order(self, force_create=False, update_pricelist=False):
        """ Return the current sales order after mofications specified by params.

        :param bool force_create: Create sales order if not already existing
        :param bool update_pricelist: Force to recompute all the lines from sales order to adapt the price with the current pricelist.
        :returns: record for the current sales order (might be empty)
        :rtype: `sale.order` recordset
        """
        self.ensure_one()

        self = self.with_company(self.company_id)
        SaleOrder = self.env['sale.order'].sudo()

        sale_order_id = request.session.get('sale_order_id')

        if sale_order_id:
            sale_order_sudo = SaleOrder.browse(sale_order_id).exists()
        elif self.env.user and not self.env.user._is_public():
            sale_order_sudo = self.env.user.partner_id.last_website_so_id
            if sale_order_sudo:
                available_pricelists = self.get_pricelist_available()
                so_pricelist_sudo = sale_order_sudo.pricelist_id
                if so_pricelist_sudo and so_pricelist_sudo not in available_pricelists:
                    # Do not reload the cart of this user last visit
                    # if the cart uses a pricelist no longer available.
                    sale_order_sudo = SaleOrder
                else:
                    # Do not reload the cart of this user last visit
                    # if the Fiscal Position has changed.
                    fpos = sale_order_sudo.env['account.fiscal.position'].with_company(
                        sale_order_sudo.company_id
                    )._get_fiscal_position(
                        sale_order_sudo.partner_id,
                        delivery=sale_order_sudo.partner_shipping_id
                    )
                    if fpos.id != sale_order_sudo.fiscal_position_id.id:
                        sale_order_sudo = SaleOrder
        else:
            sale_order_sudo = SaleOrder

        # Ignore the current order if a payment has been initiated. We don't want to retrieve the
        # cart and allow the user to update it when the payment is about to confirm it.
        if sale_order_sudo and sale_order_sudo.get_portal_last_transaction().state in (
            'pending', 'authorized', 'done'
        ):
            sale_order_sudo = None

        if not (sale_order_sudo or force_create):
            # Do not create a SO record unless needed
            if request.session.get('sale_order_id'):
                request.session.pop('sale_order_id')
                request.session.pop('website_sale_cart_quantity', None)
            return self.env['sale.order']

        # Only set when neeeded
        pricelist_id = False

        partner_sudo = self.env.user.partner_id

        if partner_sudo.company_id and not partner_sudo.filtered_domain(
            self.env['res.partner']._check_company_domain(self.company_id)
        ):
            raise UserError(_(
                "Your account is not allowed to pay in company %s."
                " Please log out and create a new account for this website, or contact the website"
                " administrator.",
                self.company_id.name,
            ))

        # cart creation was requested
        if not sale_order_sudo:
            so_data = self._prepare_sale_order_values(partner_sudo)
            sale_order_sudo = SaleOrder.with_user(SUPERUSER_ID).create(so_data)

            request.session['sale_order_id'] = sale_order_sudo.id
            request.session['website_sale_cart_quantity'] = sale_order_sudo.cart_quantity
            # The order was created with SUPERUSER_ID, revert back to request user.
            sale_order_sudo = sale_order_sudo.with_user(self.env.user).sudo()
            return sale_order_sudo

        # Existing Cart:
        #   * For logged user
        #   * In session, for specified partner

        # case when user emptied the cart
        if not request.session.get('sale_order_id'):
            request.session['sale_order_id'] = sale_order_sudo.id
            request.session['website_sale_cart_quantity'] = sale_order_sudo.cart_quantity

        # check for change of partner_id ie after signup
        if sale_order_sudo.partner_id.id != partner_sudo.id and request.website.partner_id.id != partner_sudo.id:
            previous_fiscal_position = sale_order_sudo.fiscal_position_id
            previous_pricelist = sale_order_sudo.pricelist_id

            # Reset the session pricelist according to logged partner pl
            request.session.pop('website_sale_current_pl', None)
            # Force recomputation of the website pricelist after reset
            self.invalidate_recordset(['pricelist_id'])
            pricelist_id = self.pricelist_id.id
            request.session['website_sale_current_pl'] = pricelist_id

            # change the partner, and trigger the computes (fpos)
            sale_order_sudo.write({
                'partner_id': partner_sudo.id,
                'payment_term_id': self.sale_get_payment_term(partner_sudo),
                # Must be specified to ensure it is not recomputed when it shouldn't
                'pricelist_id': pricelist_id,
            })

            if sale_order_sudo.fiscal_position_id != previous_fiscal_position:
                sale_order_sudo.order_line._compute_tax_id()

            if sale_order_sudo.pricelist_id != previous_pricelist:
                update_pricelist = True
        elif update_pricelist:
            # Only compute pricelist if needed
            pricelist_id = self.pricelist_id.id

        # update the pricelist
        if update_pricelist:
            request.session['website_sale_current_pl'] = pricelist_id
            sale_order_sudo.write({'pricelist_id': pricelist_id})
            sale_order_sudo._recompute_prices()

        return sale_order_sudo

    def _prepare_sale_order_values(self, partner_sudo):
        self.ensure_one()
        addr = partner_sudo.address_get(['delivery', 'invoice'])
        if not request.website.is_public_user():
            last_sale_order = self.env['sale.order'].sudo().search(
                [('partner_id', '=', partner_sudo.id), ('website_id', '=', self.id)],
                limit=1,
                order="date_order desc, id desc",
            )
            if last_sale_order:
                if last_sale_order.partner_shipping_id.active:  # first = me
                    addr['delivery'] = last_sale_order.partner_shipping_id.id
                if last_sale_order.partner_invoice_id.active:
                    addr['invoice'] = last_sale_order.partner_invoice_id.id

        affiliate_id = request.session.get('affiliate_id')
        salesperson_user_sudo = self.env['res.users'].sudo().browse(affiliate_id).exists()
        if not salesperson_user_sudo:
            salesperson_user_sudo = self.salesperson_id or partner_sudo.parent_id.user_id or partner_sudo.user_id

        values = {
            'company_id': self.company_id.id,

            'fiscal_position_id': self.fiscal_position_id.id,
            'partner_id': partner_sudo.id,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],

            'pricelist_id': self.pricelist_id.id,
            'payment_term_id': self.sale_get_payment_term(partner_sudo),

            'team_id': self.salesteam_id.id or partner_sudo.parent_id.team_id.id or partner_sudo.team_id.id,
            'user_id': salesperson_user_sudo.id,
            'website_id': self.id,
        }

        return values

    @api.model
    def sale_get_payment_term(self, partner):
        pt = self.env.ref('account.account_payment_term_immediate', False)
        if pt:
            pt = pt.sudo()
            pt = (not pt.company_id.id or self.company_id.id == pt.company_id.id) and pt
        return (
            partner.property_payment_term_id or
            pt or
            self.env['account.payment.term'].sudo().search([('company_id', '=', self.company_id.id)], limit=1)
        ).id

    def _get_current_fiscal_position(self):
        AccountFiscalPosition = self.env['account.fiscal.position'].sudo()
        fpos = AccountFiscalPosition
        partner_sudo = self.env.user.partner_id

        # If the current user is the website public user, the fiscal position
        # is computed according to geolocation.
        if request and request.geoip.country_code and self.partner_id.id == partner_sudo.id:
            country = self.env['res.country'].search(
                [('code', '=', request.geoip.country_code)],
                limit=1,
            )
            fpos = AccountFiscalPosition._get_fpos_by_region(country.id)

        if not fpos:
            fpos = AccountFiscalPosition._get_fiscal_position(partner_sudo)

        return fpos

    def sale_reset(self):
        request.session.pop('sale_order_id', None)
        request.session.pop('website_sale_current_pl', None)
        request.session.pop('website_sale_cart_quantity', None)

    @api.model
    def action_dashboard_redirect(self):
        if self.env.user.has_group('sales_team.group_sale_salesman'):
            return self.env["ir.actions.actions"]._for_xml_id("website.backend_dashboard")
        return super(Website, self).action_dashboard_redirect()

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('eCommerce'), url_for('/shop'), 'website_sale'))
        return suggested_controllers

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
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

    def _get_product_page_grid_image_classes(self):
        spacing_map = {
            'none': 'p-0',
            'small': 'p-2',
            'medium': 'p-3',
            'big': 'p-4',
        }
        columns_map = {
            1: 'col-12',
            2: 'col-6',
            3: 'col-4',
        }
        return spacing_map.get(self.product_page_image_spacing) + ' ' +\
                columns_map.get(self.product_page_grid_columns)

    @api.model
    def _send_abandoned_cart_email(self):
        for website in self.search([]):
            if not website.send_abandoned_cart_email:
                continue
            all_abandoned_carts = self.env['sale.order'].search([
                ('is_abandoned_cart', '=', True),
                ('cart_recovery_email_sent', '=', False),
                ('website_id', '=', website.id),
            ])
            if not all_abandoned_carts:
                continue

            abandoned_carts = all_abandoned_carts._filter_can_send_abandoned_cart_mail()
            # Mark abandoned carts that failed the filter as sent to avoid rechecking them again and again.
            (all_abandoned_carts - abandoned_carts).cart_recovery_email_sent = True
            for sale_order in abandoned_carts:
                template = self.env.ref('website_sale.mail_template_sale_cart_recovery')
                template.send_mail(sale_order.id, email_values=dict(email_to=sale_order.partner_id.email))
                sale_order.cart_recovery_email_sent = True

    def _display_partner_b2b_fields(self):
        """ This method is to be inherited by localizations and return
        True if localization should always displayed b2b fields """
        self.ensure_one()

        return self.is_view_active('website_sale.address_b2b')

    def _get_checkout_step_list(self):
        """ Return an ordered list of steps according to the current template rendered.

        :rtype: list
        :return: A list with the following structure:
            [
                [xmlid],
                {
                    'name': str,
                    'current_href': str,
                    'main_button': str,
                    'main_button_href': str,
                    'back_button': str,
                    'back_button_href': str
                }
            ]
        """
        self.ensure_one()
        is_extra_step_active = self.viewref('website_sale.extra_info').active
        redirect_to_sign_in = self.account_on_checkout == 'mandatory' and self.is_public_user()

        steps = [(['website_sale.cart'], {
            'name': _lt("Review Order"),
            'current_href': '/shop/cart',
            'main_button': _lt("Sign In") if redirect_to_sign_in else _lt("Checkout"),
            'main_button_href': f'{"/web/login?redirect=" if redirect_to_sign_in else ""}/shop/checkout?express=1',
            'back_button':  _lt("Continue shopping"),
            'back_button_href': '/shop',
        }), (['website_sale.checkout', 'website_sale.address'], {
            'name': _lt("Shipping"),
            'current_href': '/shop/checkout',
            'main_button': _lt("Confirm"),
            'main_button_href': f'{"/shop/extra_info" if is_extra_step_active else "/shop/confirm_order"}',
            'back_button':  _lt("Back to cart"),
            'back_button_href': '/shop/cart',
        })]
        if is_extra_step_active:
            steps.append((['website_sale.extra_info'], {
                'name': _lt("Extra Info"),
                'current_href': '/shop/extra_info',
                'main_button': _lt("Continue checkout"),
                'main_button_href': '/shop/confirm_order',
                'back_button':  _lt("Return to shipping"),
                'back_button_href': '/shop/checkout',
            }))
        steps.append((['website_sale.payment'], {
            'name': _lt("Payment"),
            'current_href': '/shop/payment',
            'back_button':  _lt("Back to cart"),
            'back_button_href': '/shop/cart',
        }))
        return steps

    def _get_checkout_steps(self, current_step=None):
        """ Return an ordered list of steps according to the current template rendered.
        If `current_step` is provided, returns only the corresponding step.
        Note: self.ensure_one()
        :param str current_step: The xmlid of the current step, defaults to None.
        :rtype: list
        :return: A list containing the steps generated by :meth:`_get_checkout_step_list`.
        """
        self.ensure_one()

        steps = self._get_checkout_step_list()

        if current_step:
            return next(step for step in steps if current_step in step[0])[1]
        else:
            return steps

class WebsiteSaleExtraField(models.Model):
    _name = 'website.sale.extra.field'
    _description = 'E-Commerce Extra Info Shown on product page'
    _order = 'sequence'

    website_id = fields.Many2one('website')
    sequence = fields.Integer(default=10)
    field_id = fields.Many2one(
        'ir.model.fields',
        domain=[('model_id.model', '=', 'product.template'), ('ttype', 'in', ['char', 'binary'])],
        required=True,
        ondelete='cascade'
    )
    label = fields.Char(related='field_id.field_description')
    name = fields.Char(related='field_id.name')
