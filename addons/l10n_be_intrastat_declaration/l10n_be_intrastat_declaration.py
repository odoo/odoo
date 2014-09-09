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


class account_invoice(osv.osv):
    _inherit = "account.invoice"
    _columns = {
        'incoterm_id': fields.many2one('stock.incoterms', 'Incoterm', help="International Commercial Terms are a series of predefined commercial terms used in international transactions."),
        'intrastat_transaction_id': fields.many2one('l10n_be_intrastat_declaration.transaction', 'Intrastat type of transaction', help="Intrastat nature of transaction"),
        'transport_mode_id': fields.many2one('l10n_be_intrastat_declaration.transport_mode', 'Intrastat transport mode'),
        'intrastat_country_id': fields.many2one('res.country', 'Intrastat country', help='Intrastat country, delivery for sales, origin for purchases', domain=[('intrastat','=',True)]),
    }


class intrastat_regions(osv.osv):
    _name = 'l10n_be_intrastat_declaration.regions'
    _columns = {
        'code': fields.char('Code', required=True),
        'country_id': fields.many2one('res.country', 'Country'),
        'name': fields.char('Name', translate=True),
        'description': fields.char('Description'),
    }

    _sql_constraints = [
        ('l10n_be_intrastat_declaration_regioncodeunique','UNIQUE (code)','Code must be unique.'),
    ]


class intrastat_transaction(osv.osv):
    _name = 'l10n_be_intrastat_declaration.transaction'
    _rec_name = 'code'
    _columns = {
        'code': fields.char('Code', required=True),
        'description': fields.text('Description'),
    }

    _sql_constraints = [
        ('l10n_be_intrastat_declaration_trcodeunique','UNIQUE (code)','Code must be unique.'),
    ]


class intrastat_transport_mode(osv.osv):
    _name = 'l10n_be_intrastat_declaration.transport_mode'
    _columns = {
        'code': fields.char('Code', required=True),
        'name': fields.char('Description'),
    }

    _sql_constraints = [
        ('l10n_be_intrastat_declaration_trmodecodeunique','UNIQUE (code)','Code must be unique.'),
    ]


class product_category(osv.osv):
    _name = "product.category"
    _inherit = "product.category"

    _columns = {
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat code'),
    }

    def get_intrastat_recursively(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            lstids = [ids,]
        else:
            lstids = ids
        res=[]
        categories = self.browse(cr, uid, lstids, context=context)
        for category in categories:
            if category.intrastat_id:
                res.append(category.intrastat_id.id)
            elif category.parent_id:
                res.append(self.get_intrastat_recursively(cr, uid, category.parent_id.id, context=context))
            else:
                res.append(None)
        if isinstance(ids, (int, long)):
            return res[0]
        return res


class product_product(osv.osv):
    _name = "product.product"
    _inherit = "product.product"

    def get_intrastat_recursively(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            lstids = [ids,]
        else:
            lstids = ids

        res=[]
        products = self.browse(cr, uid, lstids, context=context)
        for product in products:
            if product.intrastat_id:
                res.append(product.intrastat_id.id)
            elif product.categ_id:
                res.append(self.pool['product.category'].get_intrastat_recursively(cr, uid, product.categ_id.id, context=context))
            else:
                res.append(None)
        if isinstance(ids, (int, long)):
            return res[0]
        return res


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


class report_intrastat_code(osv.osv):
    _inherit = "report.intrastat.code"
    _columns = {
        'description': fields.text('Description', translate=True),
    }


class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'region_id': fields.many2one('l10n_be_intrastat_declaration.regions', 'Intrastat region'),
        'transport_mode_id': fields.many2one('l10n_be_intrastat_declaration.transport_mode', 'Default transport mode'),
        'incoterm_id': fields.many2one('stock.incoterms', 'Default incoterm for intrastat', help="International Commercial Terms are a series of predefined commercial terms used in international transactions."),
        'kbo': fields.char('KBO Number', help="KBO number for BNB identification."),
    }


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


class stock_warehouse(osv.osv):
    _inherit = "stock.warehouse"
    _columns = {
        'region_id': fields.many2one('l10n_be_intrastat_declaration.regions', 'Intratstat region'),
    }

    def get_regionid_from_locationid(self, cr, uid, locationid, context=None):
        location_mod = self.pool['stock.location']

        location_id = locationid
        toret = None
        stopsearching = False

        while not stopsearching:
            warehouse_ids = self.search(cr, uid, [('lot_stock_id','=',location_id)])
            if warehouse_ids and warehouse_ids[0]:
                stopsearching = True
                toret = self.browse(cr, uid, warehouse_ids[0], context=context).region_id.id
            else:
                loc = location_mod.browse(cr, uid, location_id, context=context)
                if loc and loc.location_id:
                    location_id = loc.location_id
                else:
                    #no more parent
                    stopsearching = True

        return toret
