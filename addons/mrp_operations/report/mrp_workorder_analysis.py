# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models
from openerp import tools
import openerp.addons.decimal_precision as dp


class MrpWorkorder(models.Model):
    _name = "mrp.workorder"
    _description = "Work Order Report"
    _auto = False
    nbr = fields.Integer('# of Lines', readonly=True)  # TDE FIXME master: rename into nbr_lines
    date = fields.Date('Date', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)
    category_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    product_qty = fields.Float('Product Qty', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('startworking', 'In Progress'), ('pause', 'Pause'), ('cancel', 'Cancelled'), ('done', 'Finished')], 'Status', readonly=True)
    total_hours = fields.Float('Total Hours', readonly=True)
    total_cycles = fields.Float('Total Cycles', readonly=True)
    delay = fields.Float('Delay', readonly=True)
    production_id = fields.Many2one('mrp.production', 'Production', readonly=True)
    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center', readonly=True)
    user_id = fields.Many2one('res.users', 'Responsible')
    routing_id = fields.Many2one('mrp.routing', string='Routing', readonly=True)
    bom_id = fields.Many2one('mrp.bom', 'Bill of Material', readonly=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'mrp_Workorder')
        cr.execute("""
            create or replace view mrp_Workorder as (
                select
                    date(wl.date_planned) as date,
                    min(wl.id) as id,
                    mp.product_id as product_id,
                    p.product_tmpl_id,
                    t.categ_id as category_id,
                    sum(wl.hour) as total_hours,
                    avg(wl.delay) as delay,
                    (w.costs_hour*sum(wl.hour)) as total_cost,
                    wl.production_id as production_id,
                    wl.workcenter_id as workcenter_id,
                    sum(wl.cycle) as total_cycles,
                    count(*) as nbr,
                    sum(mp.product_qty) as product_qty,
                    wl.state as state,
                    mp.user_id,
                    mp.routing_id,
                    mp.bom_id
                from mrp_production_workcenter_line wl
                    left join mrp_workcenter w on (w.id = wl.workcenter_id)
                    left join mrp_production mp on (mp.id = wl.production_id)
                    left join product_product p on (mp.product_id=p.id)
                    left join product_template t on (p.product_tmpl_id=t.id)
                group by
                    w.costs_hour, mp.product_id, mp.name, mp.user_id, mp.routing_id, mp.bom_id, wl.state, wl.date_planned, wl.production_id, wl.workcenter_id, p.product_tmpl_id, t.categ_id
        )""")
