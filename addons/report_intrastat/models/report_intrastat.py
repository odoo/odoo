# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.sql import drop_view_if_exists
from openerp.addons.decimal_precision import decimal_precision as dp


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
    _translate = False
    _columns = {
        'name': fields.char('Intrastat Code'),
        'description': fields.char('Description'),
    }



class product_template(osv.osv):
    _name = "product.template"
    _inherit = "product.template"
    _columns = {
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat code'),
    }


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
        'value': fields.float('Value', readonly=True, digits=0),
        'type': fields.selection([('import', 'Import'), ('export', 'Export')], 'Type'),
        'currency_id': fields.many2one('res.currency', "Currency", readonly=True),
        'company_id': fields.many2one('res.company', "Company", readonly=True),
    }
    def init(self, cr):
        drop_view_if_exists(cr, 'report_intrastat')
        cr.execute("""
            create or replace view report_intrastat as (
                select
                    to_char(inv.date_invoice, 'YYYY') as name,
                    to_char(inv.date_invoice, 'MM') as month,
                    min(inv_line.id) as id,
                    intrastat.id as intrastat_id,
                    upper(inv_country.code) as code,
                    sum(case when inv_line.price_unit is not null
                            then inv_line.price_unit * inv_line.quantity
                            else 0
                        end) as value,
                    sum(
                        case when uom.category_id != puom.category_id then (pt.weight * inv_line.quantity)
                        else (pt.weight * inv_line.quantity * uom.factor) end
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
                        end as type,
                    inv.company_id as company_id
                from
                    account_invoice inv
                    left join account_invoice_line inv_line on inv_line.invoice_id=inv.id
                    left join (product_template pt
                        left join product_product pp on (pp.product_tmpl_id = pt.id))
                    on (inv_line.product_id = pp.id)
                    left join product_uom uom on uom.id=inv_line.uom_id
                    left join product_uom puom on puom.id = pt.uom_id
                    left join report_intrastat_code intrastat on pt.intrastat_id = intrastat.id
                    left join (res_partner inv_address
                        left join res_country inv_country on (inv_country.id = inv_address.country_id))
                    on (inv_address.id = inv.partner_id)
                where
                    inv.state in ('open','paid')
                    and inv_line.product_id is not null
                    and inv_country.intrastat=true
                group by to_char(inv.date_invoice, 'YYYY'), to_char(inv.date_invoice, 'MM'),intrastat.id,inv.type,pt.intrastat_id, inv_country.code,inv.number,  inv.currency_id, inv.company_id
            )""")
