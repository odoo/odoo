# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
        'name': fields.date('Month', readonly=True),
        'code': fields.char('Country code', size="2", readonly=True),
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat code', readonly=True),
        'weight': fields.float('Weight', readonly=True),
        'value': fields.float('Value', readonly=True),
        'type': fields.selection([('import', 'Import'), ('export', 'Export')], 'Type'),
        'currency_id': fields.many2one('res.currency', "Currency", readonly=True),
    }
    def init(self, cr):
        cr.execute("""
            create or replace view report_intrastat as (
                select
                    to_char(m.create_date, 'YYYY-MM-01') as name,
                    min(m.id) as id,
                    pt.intrastat_id as intrastat_id,
                    case when l.usage in ('supplier', 'customer') then upper(pc.code) else upper(c.code) end as code,
                    sum(case when pol.price_unit is not null
                        then pol.price_unit * m.product_qty 
                        else
                            case when sol.price_unit is not null
                            then sol.price_unit * m.product_qty 
                            else 0 
                            end
                        end) as value,
                    sum(pt.weight_net * m.product_qty) as weight,
                    case when l.usage in ('supplier', 'customer') then 'import' else 'export' end as type,
                    case when ppl.currency_id is not null
                        then ppl.currency_id
                        else spl.currency_id
                        end as currency_id
                from
                    stock_move m
                    left join (product_template pt
                        left join product_product pp on (pp.product_tmpl_id = pt.id))
                    on (m.product_id = pt.id)
                    left join (res_partner_address a
                        left join res_country c on (c.id = a.country_id))
                    on (a.id = m.address_id)
                    left join (stock_picking sp
                        left join (res_partner_address pa
                            left join res_country pc on (pc.id = pa.country_id))
                        on (pa.id = sp.address_id))
                    on (sp.id = m.picking_id)
                    left join stock_location l on (l.id = m.location_id)
                    left join stock_location dl on (dl.id = m.location_dest_id)
                    left join (purchase_order_line pol
                        left join (purchase_order po
                            left join product_pricelist ppl on (ppl.id = po.pricelist_id))
                        on (po.id = pol.order_id))
                    on (pol.id = m.purchase_line_id)
                    left join (sale_order_line sol
                        left join (sale_order so
                            left join product_pricelist spl on (spl.id = so.pricelist_id))
                        on (so.id = sol.order_id))
                    on (sol.id = m.sale_line_id)
                where
                    m.state != 'draft'
                    and ((l.usage in ('supplier', 'customer') and dl.usage not in ('supplier', 'customer'))
                        or (dl.usage in ('supplier', 'customer') and l.usage not in ('supplier', 'customer')))
                    and (c.intrastat is not null or pc.intrastat is not null)
                group by to_char(m.create_date, 'YYYY-MM-01'), pt.intrastat_id, c.code, pc.code, l.usage, dl.usage, ppl.currency_id, spl.currency_id
            )""")
report_intrastat()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

