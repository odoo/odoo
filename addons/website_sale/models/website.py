# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools
from odoo.http import request


class Website(models.Model):
    _inherit = 'website'

    pricelist_id = fields.Many2one('product.pricelist', compute='_compute_pricelist_id', string='Default Pricelist')
    currency_id = fields.Many2one(related='pricelist_id.currency_id', string='Default Currency')
    salesperson_id = fields.Many2one('res.users', string='Salesperson')
    salesteam_id = fields.Many2one('crm.team', string='Sales Team')
    website_pricelist_ids = fields.One2many('website_pricelist', 'website_id',
                                            string='Price list available for this Ecommerce/Website')

    @api.multi
    def _compute_pricelist_id(self):
        for website in self:
            website.pricelist_id = website.get_current_pricelist()

    @tools.ormcache('self.env.uid', 'country_code', 'show_visible', 'website_pl', 'current_pl', 'all_pl')
    def _get_pl(self, country_code, show_visible, website_pl, current_pl, all_pl):
        """ Return the list of pricelists that can be used on website for the current user.

        :param str country_code: code iso or False, If set, we search only price list available for this country
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
        :param int website_pl: The default pricelist used on this website
        :param int current_pl: The current pricelist used on the website
                               (If not selectable but the current pricelist we had this pricelist anyway)
        :param list all_pl: List of all pricelist available for this website

        :returns: list of pricelist ids
        """
        pricelists = self.env['product.pricelist']

        if country_code:
            for cgroup in self.env['res.country.group'].search([('country_ids.code', '=', country_code)]):
                pricelists += cgroup.website_pricelist_ids.filtered(lambda pl: not show_visible or pl.selectable or pl.pricelist_id.id == current_pl).mapped('pricelist_id')

        if not pricelists:  # no pricelist for this country, or no GeoIP
            pricelists += all_pl.filtered(lambda pl: not show_visible or pl.selectable or pl.pricelist_id.id == current_pl).mapped('pricelist_id')

        partner = self.env.user.partner_id
        if not pricelists or partner.property_product_pricelist.id != website_pl:
            pricelists += partner.property_product_pricelist

        return pricelists.sorted(lambda pl: pl.name)

    def get_pricelist_available(self, show_visible=False):
        """ Return the list of pricelists that can be used on website for the current user.
        Country restrictions will be detected with GeoIP (if installed).

        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)

        :returns: pricelist recordset
        """
        isocountry = request.session.geoip and request.session.geoip.get('country_code') or False
        pricelists = request.website._get_pl(isocountry, show_visible,
                              request.website.user_id.partner_id.property_product_pricelist.id,
                              request.session.get('website_sale_current_pl'),
                              request.website.website_pricelist_ids)
        return pricelists

    def is_pricelist_available(self, pl_id):
        """ Return a boolean to specify if a specific pricelist can be manually set on the website.
        Warning: It check only if pricelist is in the 'selectable' pricelists or the current pricelist.

        :param int pl_id: The pricelist id to check

        :returns: Boolean, True if valid / available
        """
        return pl_id in self.get_pricelist_available(show_visible=False).mapped('id')

    def get_current_pricelist(self):
        """
        :returns: The current pricelist record
        """
        pl_id = request.session.get('website_sale_current_pl')
        if pl_id:
            pricelist = self.env['product.pricelist'].browse(pl_id)
        else:
            pricelist = self.env.user.sudo().partner_id.property_product_pricelist
            request.session['website_sale_current_pl'] = pricelist.id
        return pricelist

    @api.multi
    def sale_product_domain(self):
        return [("sale_ok", "=", True)]

    def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False):
        """ Return the current sale order after mofications specified by params.

        :param bool force_create: Create sale order if not already existing
        :param str code: Code to force a pricelist (promo code)
                         If empty, it's a special case to reset the pricelist with the first available else the default.
        :param bool update_pricelist: Force to recompute all the lines from sale order to adapt the price with the current pricelist.
        :param int force_pricelist: pricelist_id - if set,  we change the pricelist with this one

        :returns: browse record for the current sale order
        """
        partner = self.env.user.partner_id
        SaleOrderSudo = self.env['sale.order'].sudo()
        sale_order_id = request.session.get('sale_order_id') or (partner.last_website_so_id.id if partner.last_website_so_id and partner.last_website_so_id.state == 'draft' else False)

        # Test validity of the sale_order_id
        sale_order = SaleOrderSudo.browse(sale_order_id).exists() if sale_order_id else None
        pricelist_id = request.session.get('website_sale_current_pl')

        if force_pricelist and self.env['product.pricelist'].search_count([('id', '=', force_pricelist)]):
            pricelist_id = force_pricelist
            request.session['website_sale_current_pl'] = pricelist_id
            update_pricelist = True

        # create so if needed
        if not sale_order and (force_create or code):
            # TODO cache partner_id session
            affiliate_id = request.session.get('affiliate_id')
            salesperson_id = affiliate_id if self.env['res.users'].sudo().browse(affiliate_id).exists() else request.website.salesperson_id.id
            for website in self:
                addr = partner.address_get(['delivery', 'invoice'])
                values = {
                    'partner_id': partner.id,
                    'pricelist_id': pricelist_id,
                    'payment_term_id': partner.property_payment_term_id.id if partner.property_payment_term_id else False,
                    'team_id': website.salesteam_id.id,
                    'partner_invoice_id': addr['invoice'],
                    'partner_shipping_id': addr['delivery'],
                    'user_id': salesperson_id or website.salesperson_id.id,
                }
                sale_order = SaleOrderSudo.create(values)
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
                fiscal_position = sale_order.fiscal_position_id and sale_order.fiscal_position_id.id or False

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
                pricelist_ids = self.env['product.pricelist'].search([('code', '=', code)], limit=1).ids
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
                sale_order = SaleOrderSudo.browse(sale_order.id)

        else:
            request.session['sale_order_id'] = None
            return None

        return sale_order

    def sale_get_transaction(self):
        tx_id = request.session.get('sale_transaction_id')
        if tx_id:
            transactions = self.env['payment.transaction'].sudo().search([('id', '=', tx_id), ('state', 'not in', ['cancel'])])
            if transactions:
                return transactions
            else:
                request.session['sale_transaction_id'] = False
        return False

    def sale_reset(self):
        request.session.update({
            'sale_order_id': False,
            'sale_transaction_id': False,
            'website_sale_current_pl': False,
        })
