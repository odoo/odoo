# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from openerp.tools.sql import drop_view_if_exists
from openerp.addons.decimal_precision import decimal_precision as dp


class account_invoice(osv.osv):
    _inherit = "account.invoice"
    _columns = {
        'incoterm_id': fields.many2one('stock.incoterms', 'Incoterm', help="International Commercial Terms are a series of predefined commercial terms used in international transactions."),
        'intrastat_transaction_id': fields.many2one('report.intrastat.transaction', 'Intrastat type of transaction', help="Intrastat nature of transaction"),
        'transport_mode_id': fields.many2one('report.intrastat.transport_mode', 'Intrastat transport mode'),
        'intrastat_country_id': fields.many2one('res.country', 'Intrastat country', help='Intrastat country, delivery for sales, origin for purchases', domain=[('intrastat','=',True)]),
    }


class intrastat_regions(osv.osv):
    _name = 'report.intrastat.regions'
    _columns = {
        'code': fields.char('Code', required=True),
        'country_id': fields.many2one('res.country', 'Country'),
        'name': fields.char('Name', translate=True),
        'description': fields.char('Description'),
    }

    _sql_constraints = [
        ('report_intrastat_regioncodeunique','UNIQUE (code, country_id)','Code must be unique per country.'),
    ]


class intrastat_transaction(osv.osv):
    _name = 'report.intrastat.transaction'
    _rec_name = 'code'
    _columns = {
        'code': fields.char('Code', required=True),
        'description': fields.text('Description'),
    }

    _sql_constraints = [
        ('report_intrastat_trcodeunique','UNIQUE (code)','Code must be unique.'),
    ]


class intrastat_transport_mode(osv.osv):
    _name = 'report.intrastat.transport_mode'
    _columns = {
        'code': fields.char('Code', required=True),
        'name': fields.char('Description'),
    }

    _sql_constraints = [
        ('report_intrastat_trmodecodeunique','UNIQUE (code)','Code must be unique.'),
    ]


class res_country(osv.osv):
    _name = 'res.country'
    _inherit = 'res.country'
    _columns = {
        'intrastat': fields.boolean('Intrastat member'),
    }
    _defaults = {
        'intrastat': lambda *a: False,
    }



class report_intrastat_code(osv.osv):
    _name = "report.intrastat.code"
    _description = "Intrastat code"
    _columns = {
        'name': fields.char('Intrastat Code'),
        'description': fields.text('Description', translate=True),
    }


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


class product_template(osv.osv):
    _name = "product.template"
    _inherit = "product.template"
    _columns = {
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat code'),
    }


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


class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'region_id': fields.many2one('report.intrastat.regions', 'Intrastat region'),
        'transport_mode_id': fields.many2one('report.intrastat.transport_mode', 'Default transport mode'),
        'incoterm_id': fields.many2one('stock.incoterms', 'Default incoterm for intrastat', help="International Commercial Terms are a series of predefined commercial terms used in international transactions."),
    }


class stock_warehouse(osv.osv):
    _inherit = "stock.warehouse"
    _columns = {
        'region_id': fields.many2one('report.intrastat.regions', 'Intratstat region'),
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

            
class report_intrastat(osv.osv):
    _name = "report.intrastat"
    _description = "Intrastat report"
    _auto = False
    _columns = {
        'name': fields.char('Year', required=False, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month', readonly=True),
        'supply_units':fields.float('Supply Units', readonly=True),
        'ref':fields.char('Source document', readonly=True),
        'code': fields.char('Country code', size=2, readonly=True),
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat code', readonly=True),
        'weight': fields.float('Weight', readonly=True),
        'value': fields.float('Value', readonly=True, digits_compute=dp.get_precision('Account')),
        'type': fields.selection([('import', 'Import'), ('export', 'Export')], 'Type'),
        'currency_id': fields.many2one('res.currency', "Currency", readonly=True),
    }
    def init(self, cr):
        drop_view_if_exists(cr, 'report_intrastat')
        cr.execute("""
            create or replace view report_intrastat as (
                select
                    to_char(inv.create_date, 'YYYY') as name,
                    to_char(inv.create_date, 'MM') as month,
                    min(inv_line.id) as id,
                    intrastat.id as intrastat_id,
                    upper(inv_country.code) as code,
                    sum(case when inv_line.price_unit is not null
                            then inv_line.price_unit * inv_line.quantity
                            else 0
                        end) as value,
                    sum(
                        case when uom.category_id != puom.category_id then (pt.weight_net * inv_line.quantity)
                        else (pt.weight_net * inv_line.quantity * uom.factor) end
                    ) as weight,
                    sum(
                        case when uom.category_id != puom.category_id then inv_line.quantity
                        else (inv_line.quantity * uom.factor) end
                    ) as supply_units,

                    inv.currency_id as currency_id,
                    inv.number as ref,
                    case when inv.type in ('out_invoice','in_refund')
                        then 'export'
                        else 'import'
                        end as type
                from
                    account_invoice inv
                    left join account_invoice_line inv_line on inv_line.invoice_id=inv.id
                    left join (product_template pt
                        left join product_product pp on (pp.product_tmpl_id = pt.id))
                    on (inv_line.product_id = pp.id)
                    left join product_uom uom on uom.id=inv_line.uos_id
                    left join product_uom puom on puom.id = pt.uom_id
                    left join report_intrastat_code intrastat on pt.intrastat_id = intrastat.id
                    left join (res_partner inv_address
                        left join res_country inv_country on (inv_country.id = inv_address.country_id))
                    on (inv_address.id = inv.partner_id)
                where
                    inv.state in ('open','paid')
                    and inv_line.product_id is not null
                    and inv_country.intrastat=true
                group by to_char(inv.create_date, 'YYYY'), to_char(inv.create_date, 'MM'),intrastat.id,inv.type,pt.intrastat_id, inv_country.code,inv.number,  inv.currency_id
            )""")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
