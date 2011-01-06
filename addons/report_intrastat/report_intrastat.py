# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields
from tools.sql import drop_view_if_exists


class res_country(osv.osv):
    _name = 'res.country'
    _inherit = 'res.country'
    _columns = {
        'intrastat': fields.boolean('Intrastat member'),
    }
    _defaults = {
        'intrastat': lambda *a: False,
    }

res_country()


class report_intrastat_code(osv.osv):
    _name = "report.intrastat.code"
    _description = "Intrastat code"
    _columns = {
        'name': fields.char('Intrastat Code', size=16),
        'description': fields.char('Description', size=64),
    }

report_intrastat_code()


class product_template(osv.osv):
    _name = "product.template"
    _inherit = "product.template"
    _columns = {
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat code'),
    }

product_template()

class report_intrastat(osv.osv):
    _name = "report.intrastat"
    _description = "Intrastat report"
    _auto = False
    _columns = {
        'name': fields.many2one('account.period', 'Period', readonly=True, select=True),
        'supply_units':fields.float('Supply Units', readonly=True),
        'ref':fields.char('Origin',size=64, readonly=True),
        'code': fields.char('Country code', size=2, readonly=True),
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat code', readonly=True),
        'weight': fields.float('Weight', readonly=True),
        'value': fields.float('Value', readonly=True),
        'type': fields.selection([('import', 'Import'), ('export', 'Export')], 'Type'),
        'currency_id': fields.many2one('res.currency', "Currency", readonly=True),
    }
    def init(self, cr):
        drop_view_if_exists(cr, 'report_intrastat')
        cr.execute("""
            create or replace view report_intrastat as (
                select
                    inv.period_id as name,
                    min(inv_line.id) as id,
                    intrastat.id as intrastat_id,
                    upper(inv_country.code) as code,
                    sum(case when inv_line.price_unit is not null
                            then inv_line.price_unit * inv_line.quantity
                            else 0
                        end) as value,
                    sum(
                        case when uom.category_id != puom.category_id then pt.weight_net * inv_line.quantity
                        else
                            case when uom.factor_inv_data > 0
                                then
                                    pt.weight_net * inv_line.quantity * uom.factor_inv_data
                                else
                                    pt.weight_net * inv_line.quantity / uom.factor
                            end
                        end
                    ) as weight,
                    sum(
                        case when uom.category_id != puom.category_id then inv_line.quantity
                        else
                            case when uom.factor_inv_data > 0
                                then
                                    inv_line.quantity * uom.factor_inv_data
                                else
                                    inv_line.quantity / uom.factor
                            end
                        end
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
                    left join (res_partner_address inv_address
                        left join res_country inv_country on (inv_country.id = inv_address.country_id))
                    on (inv_address.id = inv.address_invoice_id)

                where
                    inv.state in ('open','paid')
                    and inv_line.product_id is not null
                    and inv_country.intrastat=true
                group by inv.period_id,intrastat.id,inv.type,pt.intrastat_id, inv_country.code,inv.number,  inv.currency_id
            )""")

report_intrastat()

