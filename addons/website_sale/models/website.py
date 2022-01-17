# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, tools, SUPERUSER_ID, _

from odoo.http import request
from odoo.addons.http_routing.models.ir_http import url_for

_logger = logging.getLogger(__name__)


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

    pricelist_id = fields.Many2one(
        'product.pricelist',
        compute='_compute_pricelist_id',
        string='Default Pricelist')
    currency_id = fields.Many2one(
        related='pricelist_id.currency_id', depends=(), related_sudo=False,
        string='Default Currency', readonly=False)
    pricelist_ids = fields.One2many('product.pricelist', compute="_compute_pricelist_ids",
                                    string='Price list available for this Ecommerce/Website')
    all_pricelist_ids = fields.One2many('product.pricelist', 'website_id', string='All pricelists',
                                        help='Technical: Used to recompute pricelist_ids')

    def _default_recovery_mail_template(self):
        try:
            return self.env.ref('website_sale.mail_template_sale_cart_recovery').id
        except ValueError:
            return False

    cart_recovery_mail_template_id = fields.Many2one('mail.template', string='Cart Recovery Email', default=_default_recovery_mail_template, domain="[('model', '=', 'sale.order')]")
    cart_abandoned_delay = fields.Float("Abandoned Delay", default=1.0)

    shop_ppg = fields.Integer(default=20, string="Number of products in the grid on the shop")
    shop_ppr = fields.Integer(default=4, string="Number of grid columns on the shop")

    @staticmethod
    def _get_product_sort_mapping():
        return [
            ('website_sequence asc', 'Featured'),
            ('create_date desc', 'Newest Arrivals'),
            ('name asc', 'Name (A-Z)'),
            ('list_price asc', 'Price - Low to High'),
            ('list_price desc', 'Price - High to Low'),
        ]
    shop_default_sort = fields.Selection(selection='_get_product_sort_mapping', default='website_sequence asc', required=True)

    shop_extra_field_ids = fields.One2many('website.sale.extra.field', 'website_id', string='E-Commerce Extra Fields')

    add_to_cart_action = fields.Selection(
        selection=[
            ('stay', 'Stay on Product Page'),
            ('go_to_cart', 'Go to cart'),
        ],
        default='stay')
    account_on_checkout = fields.Selection(
        string="Customer Accounts",
        selection=[
            ('optional', 'Optional'),
            ('disabled', 'Disabled (buy as guest)'),
            ('mandatory', 'Mandatory (no guest checkout)'),
        ],
        default='optional')

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
            website.pricelist_id = website.get_current_pricelist()

    # This method is cached, must not return records! See also #8795
    @tools.ormcache('self.env.uid', 'country_code', 'show_visible', 'website_pl', 'current_pl', 'all_pl', 'partner_pl', 'order_pl')
    def _get_pl_partner_order(self, country_code, show_visible, website_pl, current_pl, all_pl, partner_pl=False, order_pl=False):
        """ Return the list of pricelists that can be used on website for the current user.
        :param str country_code: code iso or False, If set, we search only price list available for this country
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
        :param int website_pl: The default pricelist used on this website
        :param int current_pl: The current pricelist used on the website
                               (If not selectable but the current pricelist we had this pricelist anyway)
        :param list all_pl: List of all pricelist available for this website
        :param int partner_pl: the partner pricelist
        :param int order_pl: the current cart pricelist
        :returns: list of pricelist ids
        """
        def _check_show_visible(pl):
            """ If `show_visible` is True, we will only show the pricelist if
            one of this condition is met:
            - The pricelist is `selectable`.
            - The pricelist is either the currently used pricelist or the
            current cart pricelist, we should consider it as available even if
            it might not be website compliant (eg: it is not selectable anymore,
            it is a backend pricelist, it is not active anymore..).
            """
            return (not show_visible or pl.selectable or pl.id in (current_pl, order_pl))

        # Note: 1. pricelists from all_pl are already website compliant (went through
        #          `_get_website_pricelists_domain`)
        #       2. do not read `property_product_pricelist` here as `_get_pl_partner_order`
        #          is cached and the result of this method will be impacted by that field value.
        #          Pass it through `partner_pl` parameter instead to invalidate the cache.

        # If there is a GeoIP country, find a pricelist for it
        self.ensure_one()
        pricelists = self.env['product.pricelist']
        if country_code:
            for cgroup in self.env['res.country.group'].search([('country_ids.code', '=', country_code)]):
                pricelists |= cgroup.pricelist_ids.filtered(
                    lambda pl: pl._is_available_on_website(self) and _check_show_visible(pl)
                )

        # no GeoIP or no pricelist for this country
        if not country_code or not pricelists:
            pricelists |= all_pl.filtered(lambda pl: _check_show_visible(pl))

        # if logged in, add partner pl (which is `property_product_pricelist`, might not be website compliant)
        is_public = self.user_id.id == self.env.user.id
        if not is_public:
            # keep partner_pl only if website compliant
            partner_pl = pricelists.browse(partner_pl).filtered(
                lambda pl: pl._is_available_on_website(self) and _check_show_visible(pl))
            if country_code:
                # keep partner_pl only if GeoIP compliant in case of GeoIP enabled
                partner_pl = partner_pl.filtered(
                    lambda pl: pl.country_group_ids and country_code in pl.country_group_ids.mapped('country_ids.code') or not pl.country_group_ids
                )
            pricelists |= partner_pl

        # This method is cached, must not return records! See also #8795
        return pricelists.ids

    def _get_pricelist_available(self, req, show_visible=False):
        """ Return the list of pricelists that can be used on website for the current user.
        Country restrictions will be detected with GeoIP (if installed).
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
        :returns: pricelist recordset
        """
        self.ensure_one()

        country_code = req and req.session.geoip and req.session.geoip.get('country_code') or False

        website = self.with_company(self.company_id)

        partner_sudo = website.env.user.partner_id
        last_order_pricelist = partner_sudo.last_website_so_id.pricelist_id
        partner_pricelist = partner_sudo.property_product_pricelist
        website_pricelist = website.sudo().partner_id.property_product_pricelist
        website_pricelists = website.sudo().pricelist_ids

        current_pricelist_id = req and req.session.get('website_sale_current_pl') or None

        pricelist_ids = website._get_pl_partner_order(
            country_code,
            show_visible,
            website_pricelist.id,
            current_pricelist_id,
            website_pricelists,  # TODO give as ids for better cache ?
            partner_pl=partner_pricelist.id,
            order_pl=last_order_pricelist.id)

        return self.env['product.pricelist'].browse(pricelist_ids)

    def get_pricelist_available(self, show_visible=False):
        return self._get_pricelist_available(request, show_visible)

    def is_pricelist_available(self, pl_id):
        """ Return a boolean to specify if a specific pricelist can be manually set on the website.
        Warning: It check only if pricelist is in the 'selectable' pricelists or the current pricelist.
        :param int pl_id: The pricelist id to check
        :returns: Boolean, True if valid / available
        """
        return pl_id in self.get_pricelist_available(show_visible=False).ids

    def get_current_pricelist(self):
        """
        :returns: The current pricelist record
        """
        self = self.with_company(self.company_id)

        # The list of available pricelists for this user.
        # If the user is signed in, and has a pricelist set different than the public user pricelist
        # then this pricelist will always be considered as available
        available_pricelists = self.get_pricelist_available()
        pl = None
        partner = self.env.user.partner_id
        if request and request.session.get('website_sale_current_pl'):
            # `website_sale_current_pl` is set only if the user specifically chose it:
            #  - Either, he chose it from the pricelist selection
            #  - Either, he entered a coupon code
            pl = self.env['product.pricelist'].browse(request.session['website_sale_current_pl'])
            if pl not in available_pricelists:
                pl = None
                request.session.pop('website_sale_current_pl')
        if not pl:
            # If the user has a saved cart, it take the pricelist of this last unconfirmed cart
            pl = partner.last_website_so_id.pricelist_id
            if not pl:
                # The pricelist of the user set on its partner form.
                # If the user is not signed in, it's the public user pricelist
                pl = partner.property_product_pricelist
            if available_pricelists and pl not in available_pricelists:
                # If there is at least one pricelist in the available pricelists
                # and the chosen pricelist is not within them
                # it then choose the first available pricelist.
                # This can only happen when the pricelist is the public user pricelist and this pricelist is not in the available pricelist for this localization
                # If the user is signed in, and has a special pricelist (different than the public user pricelist),
                # then this special pricelist is amongs these available pricelists, and therefore it won't fall in this case.
                pl = available_pricelists[0]

        if not pl:
            _logger.error('Fail to find pricelist for partner "%s" (id %s)', partner.name, partner.id)
        return pl

    def sale_product_domain(self):
        return [("sale_ok", "=", True)] + self.get_current_website().website_domain()

    @api.model
    def sale_get_payment_term(self, partner):
        pt = self.env.ref('account.account_payment_term_immediate', False).sudo()
        if pt:
            pt = (not pt.company_id.id or self.company_id.id == pt.company_id.id) and pt
        return (
            partner.property_payment_term_id or
            pt or
            self.env['account.payment.term'].sudo().search([('company_id', '=', self.company_id.id)], limit=1)
        ).id

    def _prepare_sale_order_values(self, partner_sudo):
        self.ensure_one()
        addr = partner_sudo.address_get(['delivery'])
        if not request.website.is_public_user():
            # FIXME VFE why not use last_website_so_id field ?
            last_sale_order = self.env['sale.order'].sudo().search(
                [('partner_id', '=', partner_sudo.id)],
                limit=1,
                order="date_order desc, id desc",
            )
            if last_sale_order and last_sale_order.partner_shipping_id.active:  # first = me
                addr['delivery'] = last_sale_order.partner_shipping_id.id

        affiliate_id = request.session.get('affiliate_id')
        salesperson_user_sudo = self.env['res.users'].sudo().browse(affiliate_id).exists()
        if not salesperson_user_sudo:
            salesperson_user_sudo = self.salesperson_id or partner_sudo.parent_id.user_id or partner_sudo.user_id

        pricelist_id = self._get_current_pricelist_id(partner_sudo)

        values = {
            'company_id': self.company_id.id,

            'partner_id': partner_sudo.id,
            'partner_invoice_id': partner_sudo.id,
            'partner_shipping_id': addr['delivery'],

            'pricelist_id': pricelist_id,
            'payment_term_id': self.sale_get_payment_term(partner_sudo),

            'team_id': self.salesteam_id.id or partner_sudo.parent_id.team_id.id or partner_sudo.team_id.id,
            'user_id': salesperson_user_sudo.id,
            'website_id': self.id,
        }

        # If the current user is the website public user, the fiscal position
        # is computed according to geolocation.
        if request.website.partner_id.id == partner_sudo.id:
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                country_id = self.env['res.country'].search([('code', '=', country_code)], limit=1).id
                values['fiscal_position_id'] = self.env['account.fiscal.position'].sudo()._get_fpos_by_region(country_id).id

        return values

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

        partner_sudo = self.env.user.partner_id
        sale_order_id = request.session.get('sale_order_id')

        if sale_order_id:
            sale_order_sudo = SaleOrder.browse(sale_order_id).exists()
        elif not self.env.user._is_public():
            sale_order_sudo = partner_sudo.last_website_so_id
            if sale_order_sudo:
                available_pricelists = self.get_pricelist_available()
                if sale_order_sudo.pricelist_id not in available_pricelists:
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

        if not (sale_order_sudo or force_create):
            # Do not create a SO record unless needed
            if request.session.get('sale_order_id'):
                request.session['sale_order_id'] = None
            return self.env['sale.order']

        # Only set when neeeded
        pricelist_id = False

        # cart creation was requested
        if not sale_order_sudo:
            # TODO cache partner_id session
            so_data = self._prepare_sale_order_values(partner_sudo)
            sale_order_sudo = SaleOrder.with_user(SUPERUSER_ID).create(so_data)

            request.session['sale_order_id'] = sale_order_sudo.id
            return sale_order_sudo

        # Existing Cart:
        #   * For logged user
        #   * In session, for specified partner

        # case when user emptied the cart
        if not request.session.get('sale_order_id'):
            request.session['sale_order_id'] = sale_order_sudo.id

        # check for change of partner_id ie after signup
        if sale_order_sudo.partner_id.id != partner_sudo.id and request.website.partner_id.id != partner_sudo.id:
            previous_fiscal_position = sale_order_sudo.fiscal_position_id
            previous_pricelist = sale_order_sudo.pricelist_id

            pricelist_id = self._get_current_pricelist_id(partner_sudo)

            # change the partner, and trigger the computes (fpos)
            sale_order_sudo.write({
                'partner_id': partner_sudo.id,
                'partner_invoice_id': partner_sudo.id,
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
            pricelist_id = self._get_current_pricelist_id(partner_sudo)

        # update the pricelist
        if update_pricelist:
            request.session['website_sale_current_pl'] = pricelist_id
            sale_order_sudo.write({'pricelist_id': pricelist_id})
            sale_order_sudo.update_prices()

        return sale_order_sudo

    def _get_current_pricelist_id(self, partner_sudo):
        return self.get_current_pricelist().id \
            or partner_sudo.property_product_pricelist.id

    def sale_reset(self):
        request.session.update({
            'sale_order_id': False,
            'website_sale_current_pl': False,
        })

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


class WebsiteSaleExtraField(models.Model):
    _name = 'website.sale.extra.field'
    _description = 'E-Commerce Extra Info Shown on product page'
    _order = 'sequence'

    website_id = fields.Many2one('website')
    sequence = fields.Integer(default=10)
    field_id = fields.Many2one(
        'ir.model.fields',
        domain=[('model_id.model', '=', 'product.template'), ('ttype', 'in', ['char', 'binary'])]
    )
    label = fields.Char(related='field_id.field_description')
    name = fields.Char(related='field_id.name')
