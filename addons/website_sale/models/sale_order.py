# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import random

from odoo import api, models, fields, tools, _
from odoo.http import request
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    website_order_line = fields.One2many(
        'sale.order.line', 'order_id',
        string='Order Lines displayed on Website', readonly=True,
        help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
    )
    cart_quantity = fields.Integer(compute='_compute_cart_info', string='Cart Quantity')
    payment_acquirer_id = fields.Many2one('payment.acquirer', string='Payment Acquirer', copy=False)
    payment_tx_id = fields.Many2one('payment.transaction', string='Transaction', copy=False)
    only_services = fields.Boolean(compute='_compute_cart_info', string='Only Services')

    @api.multi
    @api.depends('website_order_line.product_uom_qty', 'website_order_line.product_id')
    def _compute_cart_info(self):
        for order in self:
            order.cart_quantity = int(sum(order.mapped('website_order_line.product_uom_qty')))
            order.only_services = all(l.product_id.type in ('service', 'digital') for l in order.website_order_line)

    @api.model
    def _get_errors(self, order):
        return []

    @api.model
    def _get_website_data(self, order):
        return {
            'partner': order.partner_id.id,
            'order': order
        }

    @api.multi
    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        self.ensure_one()
        domain = [('order_id', '=', self.id), ('product_id', '=', product_id)]
        if line_id:
            domain += [('id', '=', line_id)]
        return self.env['sale.order.line'].sudo().search(domain)

    @api.multi
    def _website_product_id_change(self, order_id, product_id, qty=0):
        order = self.sudo().browse(order_id)
        product_context = dict(self.env.context)
        product_context.setdefault('lang', order.partner_id.lang)
        product_context.update({
            'partner': order.partner_id.id,
            'quantity': qty,
            'date': order.date_order,
            'pricelist': order.pricelist_id.id,
        })
        product = self.env['product.product'].with_context(product_context).browse(product_id)

        values = {
            'product_id': product_id,
            'name': product.display_name,
            'product_uom_qty': qty,
            'order_id': order_id,
            'product_uom': product.uom_id.id,
            'price_unit': product.price,
        }
        if product.description_sale:
            values['name'] += '\n %s' % (product.description_sale)
        return values

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        self.ensure_one()
        SaleOrderLineSudo = self.env['sale.order.line'].sudo()
        quantity = 0
        order_line = False
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(_('It is forbidden to modify a sale order which is not in draft status'))
        if line_id is not False:
            order_lines = self._cart_find_product_line(product_id, line_id, **kwargs)
            order_line = order_lines and order_lines[0]

        # Create line if no line with product_id can be located
        if not order_line:
            values = self._website_product_id_change(self.id, product_id, qty=1)
            order_line = SaleOrderLineSudo.create(values)
            order_line._compute_tax_id()
            if add_qty:
                add_qty -= 1

        # compute new quantity
        if set_qty:
            quantity = set_qty
        elif add_qty is not None:
            quantity = order_line.product_uom_qty + (add_qty or 0)

        # Remove zero of negative lines
        if quantity <= 0:
            order_line.unlink()
        else:
            # update line
            values = self._website_product_id_change(self.id, product_id, qty=quantity)
            order_line.write(values)

        return {'line_id': order_line.id, 'quantity': quantity}

    def _cart_accessories(self):
        """ Suggest accessories based on 'Accessory Products' of products in cart """
        for order in self:
            accessory_products = order.website_order_line.mapped('product_id.accessory_product_ids').filtered(lambda product: product.website_published)
            accessory_products -= order.website_order_line.mapped('product_id')
            return random.sample(accessory_products, min(len(accessory_products), 3))


class Website(models.Model):
    _inherit = 'website'

    pricelist_id = fields.Many2one('product.pricelist', compute='_compute_pricelist_id', string='Default Pricelist')
    currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', string='Default Currency')
    salesperson_id = fields.Many2one('res.users', string='Salesperson')
    salesteam_id = fields.Many2one('crm.team', string='Sales Team')
    website_pricelist_ids = fields.One2many('website_pricelist', 'website_id',
                                            string='Price list available for this Ecommerce/Website')

    @api.multi
    def _compute_pricelist_id(self):
        for website in self:
            website.pricelist_id = website.with_context(website_id=website.id).get_current_pricelist()

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
        pricelists = self.env['product.pricelist']
        if country_code:
            for cgroup in self.env['res.country.group'].search([('country_ids.code', '=', country_code)]):
                for group_pricelists in cgroup.website_pricelist_ids:
                    if not show_visible or group_pricelists.selectable or group_pricelists.pricelist_id.id in (current_pl, order_pl):
                        pricelists |= group_pricelists.pricelist_id

        if not pricelists:  # no pricelist for this country, or no GeoIP
            pricelists |= all_pl.filtered(lambda pl: not show_visible or pl.selectable or pl.pricelist_id.id in (current_pl, order_pl)).mapped('pricelist_id')

        partner = self.env.user.partner_id
        if not pricelists or partner.property_product_pricelist.id != website_pl:
            pricelists |= partner.property_product_pricelist

        return pricelists.sorted(lambda pl: pl.name)

    @tools.ormcache('self.env.uid', 'country_code', 'show_visible', 'website_pl', 'current_pl', 'all_pl')
    def _get_pl(self, country_code, show_visible, website_pl, current_pl, all_pl):
        return self._get_pl_partner_order(country_code, show_visible, website_pl, current_pl, all_pl)

    def get_pricelist_available(self, show_visible=False):

        """ Return the list of pricelists that can be used on website for the current user.
        Country restrictions will be detected with GeoIP (if installed).
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
        :returns: pricelist recordset
        """
        website = request.website
        if not request.website:
            if self.env.context.get('website_id'):
                website = self.browse(self.env.context['website_id'])
            else:
                website = self.search([], limit=1)
        isocountry = request.session.geoip and request.session.geoip.get('country_code') or False
        partner = self.env.user.partner_id
        order_pl = partner.last_website_so_id and partner.last_website_so_id.state == 'draft' and partner.last_website_so_id.pricelist_id
        partner_pl = partner.property_product_pricelist
        pricelists = website._get_pl_partner_order(isocountry, show_visible,
                                                   website.user_id.sudo().partner_id.property_product_pricelist.id,
                                                   request.session.get('website_sale_current_pl'),
                                                   website.website_pricelist_ids,
                                                   partner_pl=partner_pl and partner_pl.id or None,
                                                   order_pl=order_pl and order_pl.id or None)
        return pricelists

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
        if request.session.get('website_sale_current_pl'):
            # `website_sale_current_pl` is set only if the user specifically chose it:
            #  - Either, he chose it from the pricelist selection
            #  - Either, he entered a coupon code
            pl = self.env['product.pricelist'].browse(request.session['website_sale_current_pl'])
            if pl not in available_pricelists:
                pl = None
                request.session.pop('website_sale_current_pl')
        if not pl:
            # If the user has a saved cart, it take the pricelist of this cart, except if
            # the order is no longer draft (It has already been confirmed, or cancelled, ...)
            pl = partner.last_website_so_id.state == 'draft' and partner.last_website_so_id.pricelist_id
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

    @api.multi
    def sale_product_domain(self):
        return [("sale_ok", "=", True)]

    @api.multi
    def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False):
        """ Return the current sale order after mofications specified by params.
        :param bool force_create: Create sale order if not already existing
        :param str code: Code to force a pricelist (promo code)
                         If empty, it's a special case to reset the pricelist with the first available else the default.
        :param bool update_pricelist: Force to recompute all the lines from sale order to adapt the price with the current pricelist.
        :param int force_pricelist: pricelist_id - if set,  we change the pricelist with this one
        :returns: browse record for the current sale order
        """
        self.ensure_one()
        partner = self.env.user.partner_id
        sale_order_id = request.session.get('sale_order_id')
        if not sale_order_id:
            last_order = partner.last_website_so_id
            available_pricelists = self.get_pricelist_available()
            # Do not reload the cart of this user last visit if the cart is no longer draft or uses a pricelist no longer available.
            sale_order_id = last_order.state == 'draft' and last_order.pricelist_id in available_pricelists and last_order.id

        # Test validity of the sale_order_id
        sale_order = self.env['sale.order'].sudo().browse(sale_order_id).exists() if sale_order_id else None
        pricelist_id = request.session.get('website_sale_current_pl') or self.get_current_pricelist().id

        if self.env['product.pricelist'].browse(force_pricelist).exists():
            pricelist_id = force_pricelist
            request.session['website_sale_current_pl'] = pricelist_id
            update_pricelist = True

        # create so if needed
        if not sale_order and (force_create or code):
            # TODO cache partner_id session
            affiliate_id = request.session.get('affiliate_id')
            if self.env['res.users'].sudo().browse(affiliate_id).exists():
                salesperson_id = affiliate_id
            else:
                salesperson_id = request.website.salesperson_id.id
            addr = partner.address_get(['delivery', 'invoice'])
            sale_order = self.env['sale.order'].sudo().create({
                'partner_id': partner.id,
                'pricelist_id': pricelist_id,
                'payment_term_id': partner.property_payment_term_id.id,
                'team_id': self.salesteam_id.id,
                'partner_invoice_id': addr['invoice'],
                'partner_shipping_id': addr['delivery'],
                'user_id': salesperson_id or self.salesperson_id.id,
            })
            request.session['sale_order_id'] = sale_order.id

            if request.website.partner_id.id != partner.id:
                partner.write({'last_website_so_id': sale_order_id})

        if sale_order:

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
                sale_order.onchange_partner_id()

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
                if flag_pricelist or recent_fiscal_position != fiscal_position:
                    update_pricelist = True

            if code and code != sale_order.pricelist_id.code:
                code_pricelist = self.env['product.pricelist'].search([('code', '=', code)], limit=1)
                if code_pricelist:
                    pricelist_id = code_pricelist.id
                    update_pricelist = True
            elif code is not None and sale_order.pricelist_id.code:
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

        else:
            request.session['sale_order_id'] = None
            return None

        return sale_order

    def sale_get_transaction(self):
        tx_id = request.session.get('sale_transaction_id')
        if tx_id:
            transaction = self.env['payment.transaction'].sudo().browse(tx_id)
            if transaction.state != 'cancel':
                return transaction
            else:
                request.session['sale_transaction_id'] = False
        return False

    def sale_reset(self):
        request.session.update({
            'sale_order_id': False,
            'sale_transaction_id': False,
            'website_sale_current_pl': False,
        })

    @api.model
    def get_product_price(self, product, qty=1, public=False, **kw):
        pricelist = request.website.get_current_pricelist()
        return product.get_an_estimated_price(pricelist, qty=qty, public=public)


class WebsitePricelist(models.Model):
    _name = 'website_pricelist'
    _description = 'Website Pricelist'

    name = fields.Char('Pricelist Name', compute='_get_display_name', required=True)
    website_id = fields.Many2one('website', string="Website", required=True)
    selectable = fields.Boolean(help="Allow the end user to choose this price list")
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    country_group_ids = fields.Many2many('res.country.group', 'res_country_group_website_pricelist_rel',
                                         'website_pricelist_id', 'res_country_group_id', string='Country Groups')

    def clear_cache(self):
        # website._get_pl() is cached to avoid to recompute at each request the
        # list of available pricelists. So, we need to invalidate the cache when
        # we change the config of website price list to force to recompute.
        website = self.env['website']
        website._get_pl.clear_cache(website)
        website._get_pl_partner_order.clear_cache(website)

    @api.multi
    def _get_display_name(self):
        for website_pl in self:
            website_pl.name = _("Website Pricelist for %s") % website_pl.pricelist_id.name

    @api.model
    def create(self, data):
        res = super(WebsitePricelist, self).create(data)
        self.clear_cache()
        return res

    @api.multi
    def write(self, data):
        res = super(WebsitePricelist, self).write(data)
        self.clear_cache()
        return res

    @api.multi
    def unlink(self):
        res = super(WebsitePricelist, self).unlink()
        self.clear_cache()
        return res


class ResCountryGroup(models.Model):
    _inherit = 'res.country.group'

    website_pricelist_ids = fields.Many2many('website_pricelist', 'res_country_group_website_pricelist_rel',
                                             'res_country_group_id', 'website_pricelist_id', string='Website Price Lists')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    last_website_so_id = fields.Many2one('sale.order', string='Last Online Sale Order')
