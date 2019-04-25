# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, tools

from odoo.http import request

_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = 'website'

    pricelist_id = fields.Many2one('product.pricelist', compute='_compute_pricelist_id', string='Default Pricelist')
    currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', related_sudo=False, string='Default Currency')
    salesperson_id = fields.Many2one('res.users', string='Salesperson')
    salesteam_id = fields.Many2one('crm.team', string='Sales Channel')
    pricelist_ids = fields.One2many('product.pricelist', compute="_compute_pricelist_ids",
                                    string='Price list available for this Ecommerce/Website')

    @api.one
    def _compute_pricelist_ids(self):
        self.pricelist_ids = self.env["product.pricelist"].search([("website_id", "=", self.id)])

    @api.multi
    def _compute_pricelist_id(self):
        for website in self:
            if website._context.get('website_id') != website.id:
                website = website.with_context(website_id=website.id)
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
        pricelists = self.env['product.pricelist']
        if country_code:
            for cgroup in self.env['res.country.group'].search([('country_ids.code', '=', country_code)]):
                for group_pricelists in cgroup.pricelist_ids:
                    if not show_visible or group_pricelists.selectable or group_pricelists.id in (current_pl, order_pl):
                        pricelists |= group_pricelists

        partner = self.env.user.partner_id
        is_public = self.user_id.id == self.env.user.id
        if not is_public and (not pricelists or (partner_pl or partner.property_product_pricelist.id) != website_pl):
            if partner.property_product_pricelist.website_id:
                pricelists |= partner.property_product_pricelist

        if not pricelists:  # no pricelist for this country, or no GeoIP
            pricelists |= all_pl.filtered(lambda pl: not show_visible or pl.selectable or pl.id in (current_pl, order_pl))
        if not show_visible and not country_code:
            pricelists |= all_pl.filtered(lambda pl: pl.sudo().code)

        # This method is cached, must not return records! See also #8795
        return pricelists.ids

    def _get_pl(self, country_code, show_visible, website_pl, current_pl, all_pl):
        pl_ids = self._get_pl_partner_order(country_code, show_visible, website_pl, current_pl, all_pl)
        return self.env['product.pricelist'].browse(pl_ids)

    def get_pricelist_available(self, show_visible=False):

        """ Return the list of pricelists that can be used on website for the current user.
        Country restrictions will be detected with GeoIP (if installed).
        :param bool show_visible: if True, we don't display pricelist where selectable is False (Eg: Code promo)
        :returns: pricelist recordset
        """
        website = request and hasattr(request, 'website') and request.website or None
        if not website:
            if self.env.context.get('website_id'):
                website = self.browse(self.env.context['website_id'])
            else:
                # In the weird case we are coming from the backend (https://github.com/odoo/odoo/issues/20245)
                website = len(self) == 1 and self or self.search([], limit=1)
        isocountry = request and request.session.geoip and request.session.geoip.get('country_code') or False
        partner = self.env.user.partner_id
        order_pl = partner.last_website_so_id and partner.last_website_so_id.state == 'draft' and partner.last_website_so_id.pricelist_id
        partner_pl = partner.property_product_pricelist
        pricelists = website._get_pl_partner_order(isocountry, show_visible,
                                                   website.user_id.sudo().partner_id.property_product_pricelist.id,
                                                   request and request.session.get('website_sale_current_pl') or None,
                                                   website.pricelist_ids,
                                                   partner_pl=partner_pl and partner_pl.id or None,
                                                   order_pl=order_pl and order_pl.id or None)
        return self.env['product.pricelist'].browse(pricelists)

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

    @api.model
    def sale_get_payment_term(self, partner):
        return (
            partner.property_payment_term_id or
            self.env.ref('account.account_payment_term_immediate', False) or
            self.env['account.payment.term'].sudo().search([('company_id', '=', self.company_id.id)], limit=1)
        ).id

    @api.multi
    def _prepare_sale_order_values(self, partner, pricelist):
        self.ensure_one()
        affiliate_id = request.session.get('affiliate_id')
        salesperson_id = affiliate_id if self.env['res.users'].sudo().browse(affiliate_id).exists() else request.website.salesperson_id.id
        addr = partner.address_get(['delivery', 'invoice'])
        default_user_id = partner.parent_id.user_id.id or partner.user_id.id
        values = {
            'partner_id': partner.id,
            'pricelist_id': pricelist.id,
            'payment_term_id': self.sale_get_payment_term(partner),
            'team_id': self.salesteam_id.id or partner.parent_id.team_id.id or partner.team_id.id,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'user_id': salesperson_id or self.salesperson_id.id or default_user_id,
        }
        company = self.company_id or pricelist.company_id
        if company:
            values['company_id'] = company.id

        return values

    @api.multi
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
        if not sale_order_id:
            last_order = partner.last_website_so_id
            available_pricelists = self.get_pricelist_available()
            # Do not reload the cart of this user last visit if the cart is no longer draft or uses a pricelist no longer available.
            sale_order_id = last_order.state == 'draft' and last_order.pricelist_id in available_pricelists and last_order.id

        pricelist_id = request.session.get('website_sale_current_pl') or self.get_current_pricelist().id

        if self.env['product.pricelist'].browse(force_pricelist).exists():
            pricelist_id = force_pricelist
            request.session['website_sale_current_pl'] = pricelist_id
            update_pricelist = True

        if not self._context.get('pricelist'):
            self = self.with_context(pricelist=pricelist_id)

        # Test validity of the sale_order_id
        sale_order = self.env['sale.order'].sudo().browse(sale_order_id).exists() if sale_order_id else None

        # create so if needed
        if not sale_order and (force_create or code):
            # TODO cache partner_id session
            pricelist = self.env['product.pricelist'].browse(pricelist_id).sudo()
            so_data = self._prepare_sale_order_values(partner, pricelist)
            sale_order = self.env['sale.order'].with_context(force_company=request.website.company_id.id).sudo().create(so_data)

            # set fiscal position
            if request.website.partner_id.id != partner.id:
                sale_order.onchange_partner_shipping_id()
            else: # For public user, fiscal position based on geolocation
                country_code = request.session['geoip'].get('country_code')
                if country_code:
                    country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1).id
                    fp_id = request.env['account.fiscal.position'].sudo().with_context(force_company=request.website.company_id.id)._get_fpos_by_region(country_id)
                    sale_order.fiscal_position_id = fp_id
                else:
                    # if no geolocation, use the public user fp
                    sale_order.onchange_partner_shipping_id()

            request.session['sale_order_id'] = sale_order.id

            if request.website.partner_id.id != partner.id:
                partner.write({'last_website_so_id': sale_order.id})

        if sale_order:
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
                sale_order.onchange_partner_id()
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
                if flag_pricelist or recent_fiscal_position != fiscal_position:
                    update_pricelist = True

            if code and code != sale_order.pricelist_id.code:
                code_pricelist = self.env['product.pricelist'].sudo().search([('code', '=', code)], limit=1)
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
            return self.env['sale.order']

        return sale_order

    def sale_get_transaction(self):
        tx_id = request.session.get('sale_transaction_id')
        if tx_id:
            transaction = self.env['payment.transaction'].sudo().browse(tx_id)
            # Ugly hack for SIPS: SIPS does not allow to reuse a payment reference, even if the
            # payment was not not proceeded. For example:
            # - Select SIPS for payment
            # - Be redirected to SIPS website
            # - Go back to eCommerce without paying
            # - Be redirected to SIPS website again => error
            # Since there is no link module between 'website_sale' and 'payment_sips', we prevent
            # here to reuse any previous transaction for SIPS.
            if transaction.state != 'cancel' and transaction.acquirer_id.provider != 'sips':
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
    def action_dashboard_redirect(self):
        if self.env.user.has_group('sales_team.group_sale_salesman'):
            return self.env.ref('website.backend_dashboard').read()[0]
        return super(Website, self).action_dashboard_redirect()
