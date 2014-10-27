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
        'intrastat_transaction_id': fields.many2one('l10n_be_intrastat.transaction', 'Intrastat type of transaction', help="Intrastat nature of transaction"),
        'transport_mode_id': fields.many2one('l10n_be_intrastat.transport_mode', 'Intrastat transport mode'),
        'intrastat_country_id': fields.many2one('res.country', 'Intrastat country', help='Intrastat country, delivery for sales, origin for purchases', domain=[('intrastat','=',True)]),
    }


class intrastat_regions(osv.osv):
    _name = 'l10n_be_intrastat.regions'
    _columns = {
        'code': fields.char('Code', required=True),
        'country_id': fields.many2one('res.country', 'Country'),
        'name': fields.char('Name', translate=True),
        'description': fields.char('Description'),
    }

    _sql_constraints = [
        ('l10n_be_intrastat_regioncodeunique','UNIQUE (code)','Code must be unique.'),
    ]


class intrastat_transaction(osv.osv):
    _name = 'l10n_be_intrastat.transaction'
    _rec_name = 'code'
    _columns = {
        'code': fields.char('Code', required=True, readonmly=True),
        'description': fields.text('Description', readonly=True),
    }

    _sql_constraints = [
        ('l10n_be_intrastat_trcodeunique','UNIQUE (code)','Code must be unique.'),
    ]


class intrastat_transport_mode(osv.osv):
    _name = 'l10n_be_intrastat.transport_mode'
    _columns = {
        'code': fields.char('Code', required=True, readonmly=True),
        'name': fields.char('Description', readonmly=True),
    }

    _sql_constraints = [
        ('l10n_be_intrastat_trmodecodeunique','UNIQUE (code)','Code must be unique.'),
    ]


class product_category(osv.osv):
    _name = "product.category"
    _inherit = "product.category"

    _columns = {
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat code'),
    }

    def get_intrastat_recursively(self, cr, uid, id, context=None):
        category = self.browse(cr, uid, id, context=context)
        if category.intrastat_id:
            res = category.intrastat_id.id
        elif category.parent_id:
            res = self.get_intrastat_recursively(cr, uid, category.parent_id.id, context=context)
        else:
            res = None
        return res


class product_product(osv.osv):
    _name = "product.product"
    _inherit = "product.product"

    def get_intrastat_recursively(self, cr, uid, id, context=None):
        product = self.browse(cr, uid, id, context=context)
        if product.intrastat_id:
            res = product.intrastat_id.id
        elif product.categ_id:
            res = self.pool['product.category'].get_intrastat_recursively(cr, uid, product.categ_id.id, context=context)
        else:
            res = None
        return res


class purchase_order(osv.osv):
    _inherit = "purchase.order"

    def _prepare_invoice(self, cr, uid, order, line_ids, context=None):
        """
        copy incoterm from purchase order to invoice
        """
        invoice = super(purchase_order, self)._prepare_invoice(cr, uid, order, line_ids, context=context)
        if order.incoterm_id:
            invoice['incoterm_id'] = order.incoterm_id.id
        #Try to determinate where comes from the products
        if order.partner_id.country_id:
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
        'region_id': fields.many2one('l10n_be_intrastat.regions', 'Intrastat region'),
        'transport_mode_id': fields.many2one('l10n_be_intrastat.transport_mode', 'Default transport mode'),
        'incoterm_id': fields.many2one('stock.incoterms', 'Default incoterm for intrastat', help="International Commercial Terms are a series of predefined commercial terms used in international transactions."),
    }


class sale_order(osv.osv):
    _inherit = "sale.order"

    def _prepare_invoice(self, cr, uid, saleorder, lines, context=None):
        """
        copy incoterm from sale order to invoice
        """
        invoice = super(sale_order, self)._prepare_invoice(cr, uid, saleorder, lines, context=context)
        if saleorder.incoterm:
            invoice['incoterm_id'] = saleorder.incoterm.id
        #Try to determinate to where we send the products
        if saleorder.partner_shipping_id.country_id:
            #It comes from delivery adress
            invoice['intrastat_country_id'] = saleorder.partner_shipping_id.country_id.id
        elif saleorder.partner_id.country_id:
            #It comes from customer
            invoice['intrastat_country_id'] = saleorder.partner_id.country_id.id
        elif saleorder.partner_invoice_id.country_id:
            #It comes from invoicing adress
            invoice['intrastat_country_id'] = saleorder.partner_invoice_id.country_id.id
        return invoice


class stock_warehouse(osv.osv):
    _inherit = "stock.warehouse"
    _columns = {
        'region_id': fields.many2one('l10n_be_intrastat.regions', 'Intrastat region'),
    }

    def get_regionid_from_locationid(self, cr, uid, location_id, context=None):
        location_model = self.pool['stock.location']

        location = location_model.browse(cr, uid, location_id, context=context)
        location_ids = location_model.search(cr, uid, [('parent_left', '<=', location.parent_left), ('parent_right', '>=', location.parent_right)], context=context)
        warehouse_ids = self.search(cr, uid, [('lot_stock_id', 'in', location_ids), ('region_id', '!=', False)], context=context)
        warehouses = self.browse(cr, uid, warehouse_ids, context=context)
        if warehouses and warehouses[0]:
            return warehouses[0].region_id.id
        return None
