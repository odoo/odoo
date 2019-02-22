# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.sql import drop_view_if_exists

class ReportIntrastat(models.Model):
    _inherit = "report.intrastat"

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            create or replace view report_intrastat as (
                with category_intrastat as (
                    select DISTINCT ON(categ.id) categ.id, categs.intrastat_id
                    from product_category categ
                    inner join product_category categs on (
                        categs.intrastat_id is not null and
                        categs.parent_right > categ.parent_left and categs.parent_left <= categ.parent_left
                    ) order by categ.id, categs.parent_left desc
                )
                select
                    to_char(inv.date_invoice, 'YYYY') as name,
                    to_char(inv.date_invoice, 'MM') as month,
                    min(inv_line.id) as id,
                    coalesce(pt.intrastat_id, categ.intrastat_id) as intrastat_id,
                    upper(inv_country.code) as code,
                    sum(case when inv_line.price_unit is not null
                            then inv_line.price_unit * (1.0 - coalesce(inv_line.discount, 0.0) / 100.0) * inv_line.quantity
                            else 0
                        end) as value,
                    sum(
                        case when uom.category_id != puom.category_id then (coalesce(nullif(pp.weight, 0), pt.weight) * inv_line.quantity)
                        else (coalesce(nullif(pp.weight, 0), pt.weight) * inv_line.quantity * uom.factor) end
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
                    left join category_intrastat categ on categ.id = pt.categ_id
                    left join (res_partner inv_address
                        left join res_country inv_country on (inv_country.id = inv_address.country_id))
                    on (inv_address.id = coalesce(inv.partner_shipping_id, inv.partner_id))
                where
                    inv.state in ('open','paid')
                    and inv_line.product_id is not null
                    and inv_country.intrastat=true
                group by to_char(inv.date_invoice, 'YYYY'), to_char(inv.date_invoice, 'MM'),categ.intrastat_id,inv.type,pt.intrastat_id, inv_country.code,inv.number,  inv.currency_id, inv.company_id
            )""")
