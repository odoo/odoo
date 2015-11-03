# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import orm, fields
from odoo import SUPERUSER_ID, tools
from odoo.http import request


class website(orm.Model):
    _inherit = 'website'

    def _get_pricelist_id(self, cr, uid, ids, name, args, context=None):
        res = {}
        pricelist = self.get_current_pricelist(cr, uid, context=context)
        for data in self.browse(cr, uid, ids, context=context):
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

    @tools.ormcache('uid', 'country_code', 'show_visible', 'website_pl', 'current_pl', 'all_pl')
    def _get_pl(self, cr, uid, country_code, show_visible, website_pl, current_pl, all_pl):
        """ Return the list of pricelists that can be used on website for the current user.

        :param str country_code: code iso or False, If set, we search only price list available for this country
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
        :param int website_pl: The default pricelist used on this website
        :param int current_pl: The current pricelist used on the website
                               (If not selectable but the current pricelist we had this pricelist anyway)
        :param list all_pl: List of all pricelist available for this website

        :returns: list of pricelist ids
        """
        pcs = []

        if country_code:
            groups = self.pool['res.country.group'].search(cr, uid, [('country_ids.code', '=', country_code)])
            for cgroup in self.pool['res.country.group'].browse(cr, uid, groups):
                for pll in cgroup.website_pricelist_ids:
                    if not show_visible or pll.selectable or pll.pricelist_id.id == current_pl:
                        pcs.append(pll.pricelist_id)

        if not pcs:  # no pricelist for this country, or no GeoIP
            pcs = [pll.pricelist_id for pll in all_pl
                   if not show_visible or pll.selectable or pll.pricelist_id.id == current_pl]

        partner = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid).partner_id
        if not pcs or partner.property_product_pricelist.id != website_pl:
            pcs.append(partner.property_product_pricelist)
        # remove duplicates and sort by name
        pcs = sorted(set(pcs), key=lambda pl: pl.name)
        return [pl.id for pl in pcs]

    def get_pricelist_available(self, cr, uid, show_visible=False, context=None):
        """ Return the list of pricelists that can be used on website for the current user.
        Country restrictions will be detected with GeoIP (if installed).

        :param str country_code: code iso or False, If set, we search only price list available for this country
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)

        :returns: pricelist recordset
        """
        isocountry = request.session.geoip and request.session.geoip.get('country_code') or False
        pl_ids = self._get_pl(cr, uid, isocountry, show_visible,
                              request.website.user_id.partner_id.property_product_pricelist.id,
                              request.session.get('website_sale_current_pl'),
                              request.website.website_pricelist_ids)
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
        pl_id = request.session.get('website_sale_current_pl')
        if pl_id:
            return self.pool['product.pricelist'].browse(cr, uid, [pl_id], context=context)[0]
        else:
            pl = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id.property_product_pricelist
            request.session['website_sale_current_pl'] = pl.id
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
        sale_order_id = request.session.get('sale_order_id') or (partner.last_website_so_id.id if partner.last_website_so_id and partner.last_website_so_id.state == 'draft' else False)

        sale_order = None
        # Test validity of the sale_order_id
        if sale_order_id and sale_order_obj.exists(cr, SUPERUSER_ID, sale_order_id, context=context):
            sale_order = sale_order_obj.browse(cr, SUPERUSER_ID, sale_order_id, context=context)
        else:
            sale_order_id = None
        pricelist_id = request.session.get('website_sale_current_pl')

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
