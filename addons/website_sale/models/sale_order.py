# -*- coding: utf-8 -*-
import random
import openerp

from openerp import SUPERUSER_ID, tools
import openerp.addons.decimal_precision as dp
from openerp.osv import osv, orm, fields
from openerp.addons.web.http import request
from openerp.tools.translate import _
from openerp.exceptions import UserError


class sale_order(osv.Model):
    _inherit = "sale.order"

    def _cart_info(self, cr, uid, ids, field_name, arg, context=None):
        res = dict()
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'cart_quantity': int(sum(l.product_uom_qty for l in (order.website_order_line or []))),
                'only_services': all(l.product_id and l.product_id.type in ('service', 'digital') for l in order.website_order_line)
            }
        return res

    _columns = {
        'website_order_line': fields.one2many(
            'sale.order.line', 'order_id',
            string='Order Lines displayed on Website', readonly=True,
            help='Order Lines to be displayed on the website. They should not be used for computation purpose.',
        ),
        'cart_quantity': fields.function(_cart_info, type='integer', string='Cart Quantity', multi='_cart_info'),
        'payment_acquirer_id': fields.many2one('payment.acquirer', 'Payment Acquirer', on_delete='set null', copy=False),
        'payment_tx_id': fields.many2one('payment.transaction', 'Transaction', on_delete='set null', copy=False),
        'only_services': fields.function(_cart_info, type='boolean', string='Only Services', multi='_cart_info'),
    }

    def _get_errors(self, cr, uid, order, context=None):
        return []

    def _get_website_data(self, cr, uid, order, context):
        return {
            'partner': order.partner_id.id,
            'order': order
        }

    def _cart_find_product_line(self, cr, uid, ids, product_id=None, line_id=None, context=None, **kwargs):
        for so in self.browse(cr, uid, ids, context=context):
            domain = [('order_id', '=', so.id), ('product_id', '=', product_id)]
            if line_id:
                domain += [('id', '=', line_id)]
            return self.pool.get('sale.order.line').search(cr, SUPERUSER_ID, domain, context=context)

    def _website_product_id_change(self, cr, uid, ids, order_id, product_id, qty=0, context=None):
        context = dict(context or {})
        order = self.pool['sale.order'].browse(cr, SUPERUSER_ID, order_id, context=context)
        product_context = context.copy()
        product_context.update({
            'lang': order.partner_id.lang,
            'partner': order.partner_id.id,
            'quantity': qty,
            'date': order.date_order,
            'pricelist': order.pricelist_id.id,
        })
        product = self.pool['product.product'].browse(cr, uid, product_id, context=product_context)

        values = {
            'product_id': product_id,
            'name': product.display_name,
            'product_uom_qty': qty,
            'order_id': order_id,
            'product_uom': product.uom_id.id,
            'price_unit': product.price,
        }
        if product.description_sale:
            values['name'] += '\n' + product.description_sale
        return values

    def _cart_update(self, cr, uid, ids, product_id=None, line_id=None, add_qty=0, set_qty=0, context=None, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        sol = self.pool.get('sale.order.line')

        quantity = 0
        for so in self.browse(cr, uid, ids, context=context):
            if so.state != 'draft':
                request.session['sale_order_id'] = None
                raise UserError(_('It is forbidden to modify a sale order which is not in draft status'))
            if line_id is not False:
                line_ids = so._cart_find_product_line(product_id, line_id, context=context, **kwargs)
                if line_ids:
                    line_id = line_ids[0]

            # Create line if no line with product_id can be located
            if not line_id:
                values = self._website_product_id_change(cr, uid, ids, so.id, product_id, qty=1, context=context)
                line_id = sol.create(cr, SUPERUSER_ID, values, context=context)
                sol._compute_tax_id(cr, SUPERUSER_ID, [line_id], context=context)
                if add_qty:
                    add_qty -= 1

            # compute new quantity
            if set_qty:
                quantity = set_qty
            elif add_qty is not None:
                quantity = sol.browse(cr, SUPERUSER_ID, line_id, context=context).product_uom_qty + (add_qty or 0)

            # Remove zero of negative lines
            if quantity <= 0:
                sol.unlink(cr, SUPERUSER_ID, [line_id], context=context)
            else:
                # update line
                values = self._website_product_id_change(cr, uid, ids, so.id, product_id, qty=quantity, context=context)
                sol.write(cr, SUPERUSER_ID, [line_id], values, context=context)

        return {'line_id': line_id, 'quantity': quantity}

    def _cart_accessories(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            s = set(j.id for l in (order.website_order_line or []) for j in (l.product_id.accessory_product_ids or []) if j.website_published)
            s -= set(l.product_id.id for l in order.order_line)
            product_ids = random.sample(s, min(len(s), 3))
            return self.pool['product.product'].browse(cr, uid, product_ids, context=context)

class sale_order_line(osv.Model):
    _inherit = "sale.order.line"

    def _fnct_get_discounted_price(self, cr, uid, ids, field_name, args, context=None):
        res = dict.fromkeys(ids, False)
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = (line.price_unit * (1.0 - (line.discount or 0.0) / 100.0))
        return res

    _columns = {
        'discounted_price': fields.function(_fnct_get_discounted_price, string='Discounted price', type='float', digits_compute=dp.get_precision('Product Price')),
    }


class website(orm.Model):
    _inherit = 'website'

    def _get_pricelist_id(self, cr, uid, ids, name, args, context=None):
        res = {}
        for data in self.browse(cr, uid, ids, context=context):
            pricelist = self.get_current_pricelist(cr, uid, context=dict(context, website_id=data.id))
            res[data.id] = pricelist.id
        return res

    _columns = {
        'pricelist_id': fields.function(_get_pricelist_id,\
            type='many2one', relation="product.pricelist", string='Default Pricelist'),
        'currency_id': fields.related(
            'pricelist_id', 'currency_id',
            type='many2one', relation='res.currency', string='Default Currency'),
        'salesperson_id': fields.many2one('res.users', 'Salesperson'),
        'salesteam_id': fields.many2one('crm.team', 'Sales Team'),
        'website_pricelist_ids': fields.one2many('website_pricelist', 'website_id',
                                                 string='Price list available for this Ecommerce/Website'),
    }

    @tools.ormcache('uid', 'country_code', 'show_visible', 'website_pl', 'current_pl', 'all_pl', 'partner_pl', 'order_pl')
    def _get_pl_partner_order(self, cr, uid, country_code, show_visible, website_pl, current_pl, all_pl, partner_pl=False, order_pl=False):
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
        pcs = []

        if country_code:
            groups = self.pool['res.country.group'].search(cr, uid, [('country_ids.code', '=', country_code)])
            for cgroup in self.pool['res.country.group'].browse(cr, uid, groups):
                for pll in cgroup.website_pricelist_ids:
                    if not show_visible or pll.selectable or pll.pricelist_id.id in (current_pl, order_pl):
                        pcs.append(pll.pricelist_id)

        if not pcs:  # no pricelist for this country, or no GeoIP
            pcs = [pll.pricelist_id for pll in all_pl
                   if not show_visible or pll.selectable or pll.pricelist_id.id in (current_pl, order_pl)]

        partner = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid).partner_id
        if not pcs or partner.property_product_pricelist.id != website_pl:
            pcs.append(partner.property_product_pricelist)
        # remove duplicates and sort by name
        pcs = sorted(set(pcs), key=lambda pl: pl.name)
        return [pl.id for pl in pcs]

    @tools.ormcache('uid', 'country_code', 'show_visible', 'website_pl', 'current_pl', 'all_pl')
    def _get_pl(self, cr, uid, country_code, show_visible, website_pl, current_pl, all_pl):
        return self._get_pl_partner_order(cr, uid, country_code, show_visible, website_pl, current_pl, all_pl)

    def get_pricelist_available(self, cr, uid, show_visible=False, context=None):
        """ Return the list of pricelists that can be used on website for the current user.
        Country restrictions will be detected with GeoIP (if installed).

        :param str country_code: code iso or False, If set, we search only price list available for this country
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)

        :returns: pricelist recordset
        """
        website = request.website
        if not request.website:
            if context.get('website_id'):
                website_id = context['website_id']
            else:
                website_id = self.search(cr, uid, [], context=context)
            website = self.browse(cr, uid, website_id, context=context)
        isocountry = request.session.geoip and request.session.geoip.get('country_code') or False
        partner = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        order_pl = partner.last_website_so_id and partner.last_website_so_id.state == 'draft' and partner.last_website_so_id.pricelist_id
        partner_pl = partner.property_product_pricelist
        pl_ids = self._get_pl_partner_order(cr, uid, isocountry, show_visible,
                                            website.user_id.sudo().partner_id.property_product_pricelist.id,
                                            request.session.get('website_sale_current_pl'),
                                            website.website_pricelist_ids,
                                            partner_pl=partner_pl and partner_pl.id or None,
                                            order_pl=order_pl and order_pl.id or None)
        return self.pool['product.pricelist'].browse(cr, uid, pl_ids, context=context)

    def is_pricelist_available(self, cr, uid, pl_id, context=None):
        """ Return a boolean to specify if a specific pricelist can be manually set on the website.
        Warning: It check only if pricelist is in the 'selectable' pricelists or the current pricelist.

        :param int pl_id: The pricelist id to check

        :returns: Boolean, True if valid / available
        """
        return pl_id in [ppl.id for ppl in self.get_pricelist_available(cr, uid, show_visible=False, context=context)]

    def get_current_pricelist(self, cr, uid, context=None):
        """
        :returns: The current pricelist record
        """
        # The list of available pricelists for this user.
        # If the user is signed in, and has a pricelist set different than the public user pricelist
        # then this pricelist will always be considered as available
        available_pricelists = self.get_pricelist_available(cr, uid, context=context)
        pl = None
        if request.session.get('website_sale_current_pl'):
            # `website_sale_current_pl` is set only if the user specifically chose it:
            #  - Either, he chose it from the pricelist selection
            #  - Either, he entered a coupon code
            pl = self.pool['product.pricelist'].browse(cr, uid, [request.session['website_sale_current_pl']], context=context)[0]
            if pl not in available_pricelists:
                pl = None
                request.session.pop('website_sale_current_pl')
        if not pl:
            partner = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id
            # If the user has a saved cart, it take the pricelist of this cart, except if
            # the order is no longer draft (It has already been confirmed, or cancelled, ...)
            pl = partner.last_website_so_id and partner.last_website_so_id.state == 'draft' and partner.last_website_so_id.pricelist_id
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

        return pl

    def sale_product_domain(self, cr, uid, ids, context=None):
        return [("sale_ok", "=", True)]

    def get_partner(self, cr, uid):
        return self.pool['res.users'].browse(cr, SUPERUSER_ID, uid).partner_id

    def sale_get_order(self, cr, uid, ids, force_create=False, code=None, update_pricelist=False, force_pricelist=False, context=None):
        """ Return the current sale order after mofications specified by params.

        :param bool force_create: Create sale order if not already existing
        :param str code: Code to force a pricelist (promo code)
                         If empty, it's a special case to reset the pricelist with the first available else the default.
        :param bool update_pricelist: Force to recompute all the lines from sale order to adapt the price with the current pricelist.
        :param int force_pricelist: pricelist_id - if set,  we change the pricelist with this one

        :returns: browse record for the current sale order
        """
        partner = self.get_partner(cr, uid)
        sale_order_obj = self.pool['sale.order']
        sale_order_id = request.session.get('sale_order_id')
        if not sale_order_id:
            last_order = partner.last_website_so_id
            available_pricelists = self.get_pricelist_available(cr, uid, context=context)
            # Do not reload the cart of this user last visit if the cart is no longer draft or uses a pricelist no longer available.
            sale_order_id = last_order and last_order.state == 'draft' and last_order.pricelist_id in available_pricelists and last_order.id

        sale_order = None
        # Test validity of the sale_order_id
        if sale_order_id and sale_order_obj.exists(cr, SUPERUSER_ID, sale_order_id, context=context):
            sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order_id, context=context)
        else:
            sale_order_id = None
        pricelist_id = request.session.get('website_sale_current_pl') or self.get_current_pricelist(cr, uid, context=context).id

        if force_pricelist and self.pool['product.pricelist'].search_count(cr, uid, [('id', '=', force_pricelist)], context=context):
            pricelist_id = force_pricelist
            request.session['website_sale_current_pl'] = pricelist_id
            update_pricelist = True

        # create so if needed
        if not sale_order_id and (force_create or code):
            # TODO cache partner_id session
            user_obj = self.pool['res.users']
            affiliate_id = request.session.get('affiliate_id')
            salesperson_id = affiliate_id if user_obj.exists(cr, SUPERUSER_ID, affiliate_id, context=context) else request.website.salesperson_id.id
            for w in self.browse(cr, uid, ids):
                addr = partner.address_get(['delivery', 'invoice'])
                values = {
                    'partner_id': partner.id,
                    'pricelist_id': pricelist_id,
                    'payment_term_id': partner.property_payment_term_id.id if partner.property_payment_term_id else False,
                    'team_id': w.salesteam_id.id,
                    'partner_invoice_id': addr['invoice'],
                    'partner_shipping_id': addr['delivery'],
                    'user_id': salesperson_id or w.salesperson_id.id,
                }
                sale_order_id = sale_order_obj.create(cr, SUPERUSER_ID, values, context=context)
                request.session['sale_order_id'] = sale_order_id
                sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order_id, context=context)

                if request.website.partner_id.id != partner.id:
                    self.pool['res.partner'].write(cr, SUPERUSER_ID, partner.id, {'last_website_so_id': sale_order_id})

        if sale_order_id:

            # check for change of pricelist with a coupon
            pricelist_id = pricelist_id or partner.property_product_pricelist.id

            # check for change of partner_id ie after signup
            if sale_order.partner_id.id != partner.id and request.website.partner_id.id != partner.id:
                flag_pricelist = False
                if pricelist_id != sale_order.pricelist_id.id:
                    flag_pricelist = True
                fiscal_position = sale_order.fiscal_position_id and sale_order.fiscal_position_id.id or False

                # change the partner, and trigger the onchange
                sale_order_obj.write(cr, SUPERUSER_ID, [sale_order_id], {'partner_id': partner.id}, context=context)
                sale_order_obj.onchange_partner_id(cr, SUPERUSER_ID, [sale_order_id], context=context)

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
                    sale_order_obj.write(cr, SUPERUSER_ID, [sale_order_id], values, context=context)

                # check if the fiscal position has changed with the partner_id update
                recent_fiscal_position = sale_order.fiscal_position_id and sale_order.fiscal_position_id.id or False
                if flag_pricelist or recent_fiscal_position != fiscal_position:
                    update_pricelist = True

            if code and code != sale_order.pricelist_id.code:
                pricelist_ids = self.pool['product.pricelist'].search(cr, uid, [('code', '=', code)], limit=1, context=context)
                if pricelist_ids:
                    pricelist_id = pricelist_ids[0]
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

            # update browse record
            if (code and code != sale_order.pricelist_id.code) or sale_order.partner_id.id != partner.id or force_pricelist:
                sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order.id, context=context)

        else:
            request.session['sale_order_id'] = None
            return None

        return sale_order

    def sale_get_transaction(self, cr, uid, ids, context=None):
        transaction_obj = self.pool.get('payment.transaction')
        tx_id = request.session.get('sale_transaction_id')
        if tx_id:
            tx_ids = transaction_obj.search(cr, SUPERUSER_ID, [('id', '=', tx_id), ('state', 'not in', ['cancel'])], context=context)
            if tx_ids:
                return transaction_obj.browse(cr, SUPERUSER_ID, tx_ids[0], context=context)
            else:
                request.session['sale_transaction_id'] = False
        return False

    def sale_reset(self, cr, uid, ids, context=None):
        request.session.update({
            'sale_order_id': False,
            'sale_transaction_id': False,
            'website_sale_current_pl': False,
        })


class website_pricelist(osv.Model):
    _name = 'website_pricelist'
    _description = 'Website Pricelist'

    def _get_display_name(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for o in self.browse(cr, uid, ids, context=context):
            result[o.id] = _("Website Pricelist for %s") % o.pricelist_id.name
        return result

    _columns = {
        'name': fields.function(_get_display_name, string='Pricelist Name', type="char"),
        'website_id': fields.many2one('website', string="Website", required=True),
        'selectable': fields.boolean('Selectable', help="Allow the end user to choose this price list"),
        'pricelist_id': fields.many2one('product.pricelist', string='Pricelist'),
        'country_group_ids': fields.many2many('res.country.group', 'res_country_group_website_pricelist_rel',
                                              'website_pricelist_id', 'res_country_group_id', string='Country Groups'),
    }

    def clear_cache(self):
        # website._get_pl() is cached to avoid to recompute at each request the
        # list of available pricelists. So, we need to invalidate the cache when
        # we change the config of website price list to force to recompute.
        website = self.pool['website']
        website._get_pl.clear_cache(website)
        website._get_pl_partner_order.clear_cache(website)

    def create(self, cr, uid, data, context=None):
        res = super(website_pricelist, self).create(cr, uid, data, context=context)
        self.clear_cache()
        return res

    def write(self, cr, uid, ids, data, context=None):
        res = super(website_pricelist, self).write(cr, uid, ids, data, context=context)
        self.clear_cache()
        return res

    def unlink(self, cr, uid, ids, context=None):
        res = super(website_pricelist, self).unlink(cr, uid, ids, context=context)
        self.clear_cache()
        return res


class CountryGroup(osv.Model):
    _inherit = 'res.country.group'
    _columns = {
        'website_pricelist_ids': fields.many2many('website_pricelist', 'res_country_group_website_pricelist_rel',
                                                  'res_country_group_id', 'website_pricelist_id', string='Website Price Lists'),
    }


class res_partner(openerp.models.Model):
    _inherit = 'res.partner'

    last_website_so_id = openerp.fields.Many2one('sale.order', 'Last Online Sale Order')
