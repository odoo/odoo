# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, tools, SUPERUSER_ID, _

from odoo.http import request
from odoo.addons.website.models import ir_http
from odoo.addons.http_routing.models.ir_http import url_for

_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = 'website'

    pricelist_id = fields.Many2one('product.pricelist', compute='_compute_pricelist_id', string='Default Pricelist')
    currency_id = fields.Many2one('res.currency',
        related='pricelist_id.currency_id', depends=(), related_sudo=False,
        string='Default Currency', readonly=False)
    salesperson_id = fields.Many2one('res.users', string='Salesperson')

    def _get_default_website_team(self):
        try:
            team = self.env.ref('sales_team.salesteam_website_sales')
            return team if team.active else None
        except ValueError:
            return None

    salesteam_id = fields.Many2one('crm.team',
        string='Sales Team', ondelete="set null",
        default=_get_default_website_team)
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

    shop_extra_field_ids = fields.One2many('website.sale.extra.field', 'website_id', string='E-Commerce Extra Fields')

    cart_add_on_page = fields.Boolean("Stay on page after adding to cart", default=True)

    @api.depends('all_pricelist_ids')
    def _compute_pricelist_ids(self):
        Pricelist = self.env['product.pricelist']
        for website in self:
            website.pricelist_ids = Pricelist.search(
                Pricelist._get_website_pricelists_domain(website.id)
            )

    def _compute_pricelist_id(self):
        for website in self:
            website.pricelist_id = website.with_context(website_id=website.id).get_current_pricelist()

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
                    lambda pl: pl._is_available_on_website(self.id) and _check_show_visible(pl)
                )

        # no GeoIP or no pricelist for this country
        if not country_code or not pricelists:
            pricelists |= all_pl.filtered(lambda pl: _check_show_visible(pl))

        # if logged in, add partner pl (which is `property_product_pricelist`, might not be website compliant)
        is_public = self.user_id.id == self.env.user.id
        if not is_public:
            # keep partner_pl only if website compliant
            partner_pl = pricelists.browse(partner_pl).filtered(lambda pl: pl._is_available_on_website(self.id) and _check_show_visible(pl))
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
        website = ir_http.get_request_website()
        if not website:
            if self.env.context.get('website_id'):
                website = self.browse(self.env.context['website_id'])
            else:
                # In the weird case we are coming from the backend (https://github.com/odoo/odoo/issues/20245)
                website = len(self) == 1 and self or self.search([], limit=1)
        isocountry = req and req.session.geoip and req.session.geoip.get('country_code') or False
        partner = self.env.user.partner_id
        last_order_pl = partner.last_website_so_id.pricelist_id
        partner_pl = partner.property_product_pricelist
        pricelists = website._get_pl_partner_order(isocountry, show_visible,
                                                   website.user_id.sudo().partner_id.property_product_pricelist.id,
                                                   req and req.session.get('website_sale_current_pl') or None,
                                                   website.pricelist_ids,
                                                   partner_pl=partner_pl and partner_pl.id or None,
                                                   order_pl=last_order_pl and last_order_pl.id or None)
        return self.env['product.pricelist'].browse(pricelists)

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

    def _prepare_sale_order_values(self, partner, pricelist):
        self.ensure_one()
        affiliate_id = request.session.get('affiliate_id')
        salesperson_id = affiliate_id if self.env['res.users'].sudo().browse(affiliate_id).exists() else request.website.salesperson_id.id
        addr = partner.address_get(['delivery'])
        if not request.website.is_public_user():
            last_sale_order = self.env['sale.order'].sudo().search([('partner_id', '=', partner.id)], limit=1, order="date_order desc, id desc")
            if last_sale_order and last_sale_order.partner_shipping_id.active:  # first = me
                addr['delivery'] = last_sale_order.partner_shipping_id.id
        default_user_id = partner.parent_id.user_id.id or partner.user_id.id
        values = {
            'partner_id': partner.id,
            'pricelist_id': pricelist.id,
            'payment_term_id': self.sale_get_payment_term(partner),
            'team_id': self.salesteam_id.id or partner.parent_id.team_id.id or partner.team_id.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': addr['delivery'],
            'user_id': salesperson_id or self.salesperson_id.id or default_user_id,
            'website_id': self._context.get('website_id'),
            'company_id': self.company_id.id,
        }
        return values

    def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False):
        """ Return the current sales order after mofications specified by params.
        :param bool force_create: Create sales order if not already existing
        :param str code: Code to force a pricelist (promo code)
                         If empty, it's a special case to reset the pricelist with the first available else the default.
        :param bool update_pricelist: Force to recompute all the lines from sales order to adapt the price with the current pricelist.
        :param int force_pricelist: pricelist_id - if set,  we change the pricelist with this one
        :returns: browse record for the current sales order
        """
        self.ensure_one()
        partner = self.env.user.partner_id
        sale_order_id = request.session.get('sale_order_id')
        check_fpos = False
        if not sale_order_id and not self.env.user._is_public():
            last_order = partner.last_website_so_id
            if last_order:
                available_pricelists = self.get_pricelist_available()
                # Do not reload the cart of this user last visit if the cart uses a pricelist no longer available.
                sale_order_id = last_order.pricelist_id in available_pricelists and last_order.id
                check_fpos = True

        # Test validity of the sale_order_id
        sale_order = self.env['sale.order'].with_company(request.website.company_id.id).sudo().browse(sale_order_id).exists() if sale_order_id else None

        # Ignore the current order if a payment has been initiated. We don't want to retrieve the
        # cart and allow the user to update it when the payment is about to confirm it.
        if sale_order and sale_order.get_portal_last_transaction().state in ('pending', 'authorized', 'done'):
            sale_order = None

        # Do not reload the cart of this user last visit if the Fiscal Position has changed.
        if check_fpos and sale_order:
            fpos_id = (
                self.env['account.fiscal.position'].sudo()
                .with_company(sale_order.company_id.id)
                .get_fiscal_position(sale_order.partner_id.id, delivery_id=sale_order.partner_shipping_id.id)
            ).id
            if sale_order.fiscal_position_id.id != fpos_id:
                sale_order = None

        if not (sale_order or force_create or code):
            if request.session.get('sale_order_id'):
                request.session['sale_order_id'] = None
            return self.env['sale.order']

        if self.env['product.pricelist'].browse(force_pricelist).exists():
            pricelist_id = force_pricelist
            request.session['website_sale_current_pl'] = pricelist_id
            update_pricelist = True
        else:
            pricelist_id = request.session.get('website_sale_current_pl') or self.get_current_pricelist().id

        if not self._context.get('pricelist'):
            self = self.with_context(pricelist=pricelist_id)

        # cart creation was requested (either explicitly or to configure a promo code)
        if not sale_order:
            # TODO cache partner_id session
            pricelist = self.env['product.pricelist'].browse(pricelist_id).sudo()
            so_data = self._prepare_sale_order_values(partner, pricelist)
            sale_order = self.env['sale.order'].with_company(request.website.company_id.id).with_user(SUPERUSER_ID).create(so_data)

            # set fiscal position
            if request.website.partner_id.id != partner.id:
                sale_order.onchange_partner_shipping_id()
            else: # For public user, fiscal position based on geolocation
                country_code = request.session['geoip'].get('country_code')
                if country_code:
                    country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1).id
                    sale_order.fiscal_position_id = request.env['account.fiscal.position'].sudo().with_company(request.website.company_id.id)._get_fpos_by_region(country_id)
                else:
                    # if no geolocation, use the public user fp
                    sale_order.onchange_partner_shipping_id()

            request.session['sale_order_id'] = sale_order.id

            # The order was created with SUPERUSER_ID, revert back to request user.
            sale_order = sale_order.with_user(self.env.user).sudo()

        # case when user emptied the cart
        if not request.session.get('sale_order_id'):
            request.session['sale_order_id'] = sale_order.id

        # check for change of pricelist with a coupon
        pricelist_id = pricelist_id or partner.property_product_pricelist.id

        # check for change of partner_id ie after signup
        if sale_order.partner_id.id != partner.id and request.website.partner_id.id != partner.id:
            flag_pricelist = False
            if pricelist_id != sale_order.pricelist_id.id:
                flag_pricelist = True
            fiscal_position = sale_order.fiscal_position_id.id

            # change the partner, and trigger the onchange
            sale_order.write({'partner_id': partner.id})
            sale_order.with_context(not_self_saleperson=True).onchange_partner_id()
            sale_order.write({'partner_invoice_id': partner.id})
            sale_order.onchange_partner_shipping_id() # fiscal position
            sale_order['payment_term_id'] = self.sale_get_payment_term(partner)

            # check the pricelist : update it if the pricelist is not the 'forced' one
            values = {}
            if sale_order.pricelist_id:
                if sale_order.pricelist_id.id != pricelist_id:
                    values['pricelist_id'] = pricelist_id
                    update_pricelist = True

            # if fiscal position, update the order lines taxes
            if sale_order.fiscal_position_id:
                sale_order._compute_tax_id()

            # if values, then make the SO update
            if values:
                sale_order.write(values)

            # check if the fiscal position has changed with the partner_id update
            recent_fiscal_position = sale_order.fiscal_position_id.id
            # when buying a free product with public user and trying to log in, SO state is not draft
            if (flag_pricelist or recent_fiscal_position != fiscal_position) and sale_order.state == 'draft':
                update_pricelist = True

        if code and code != sale_order.pricelist_id.code:
            code_pricelist = self.env['product.pricelist'].sudo().search([('code', '=', code)], limit=1)
            if code_pricelist:
                pricelist_id = code_pricelist.id
                update_pricelist = True
        elif code is not None and sale_order.pricelist_id.code and code != sale_order.pricelist_id.code:
            # code is not None when user removes code and click on "Apply"
            pricelist_id = partner.property_product_pricelist.id
            update_pricelist = True

        # update the pricelist
        if update_pricelist:
            request.session['website_sale_current_pl'] = pricelist_id
            values = {'pricelist_id': pricelist_id}
            sale_order.write(values)
            for line in sale_order.order_line:
                if line.exists():
                    sale_order._cart_update(product_id=line.product_id.id, line_id=line.id, add_qty=0)

        return sale_order

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
