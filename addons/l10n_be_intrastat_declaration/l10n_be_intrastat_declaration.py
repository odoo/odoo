# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import fields, osv


class purchase_order(osv.osv):
    _inherit = "purchase.order"

    def _prepare_invoice(self, cr, uid, order, line_ids, context=None):
        """
        copy incoterm from purchase order to invoice
        """
        invoice = super(purchase_order, self)._prepare_invoice(cr, uid, order, line_ids, context=context)
        if order.incoterm_id and order.incoterm_id.id:
            invoice['incoterm_id'] = order.incoterm_id.id
        #Try to determinate where comes from the products
        if order.partner_id and order.partner_id.country_id and order.partner_id.country_id.id:
            #It comes from supplier
            invoice['intrastat_country_id'] = order.partner_id.country_id.id

        return invoice


class sale_order(osv.osv):
    _inherit = "sale.order"

    def _prepare_invoice(self, cr, uid, saleorder, lines, context=None):
        """
        copy incoterm from sale order to invoice
        """
        invoice = super(sale_order, self)._prepare_invoice(cr, uid, saleorder, lines, context=context)
        if saleorder.incoterm and saleorder.incoterm.id:
            invoice['incoterm_id'] = saleorder.incoterm.id
        #Try to determinate to where we send the products
        if saleorder.partner_shipping_id and saleorder.partner_shipping_id.country_id and saleorder.partner_shipping_id.country_id.id:
            #It comes from delivery adress
            invoice['intrastat_country_id'] = saleorder.partner_shipping_id.country_id.id
        elif saleorder.partner_id and saleorder.partner_id.country_id and saleorder.partner_id.country_id.id:
            #It comes from customer
            invoice['intrastat_country_id'] = saleorder.partner_id.country_id.id
        elif saleorder.partner_invoice_id and saleorder.partner_invoice_id.country_id and saleorder.partner_invoice_id.country_id.id:
            #It comes from invoicing adress
            invoice['intrastat_country_id'] = saleorder.partner_invoice_id.country_id.id
        return invoice

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'kbo': fields.char('KBO Number', help="KBO number for BNB identification."),
    }
