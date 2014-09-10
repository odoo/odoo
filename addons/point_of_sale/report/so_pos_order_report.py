# -*- coding: utf-8 -*-

from openerp import models, fields
from openerp import tools

class so_pos_order_report(models.Model):
    _name = "report.so.pos.order"
    _description = "Sale and Point of Sale Orders Statistics"
    _auto = False
    _order = 'date desc'

    date = fields.Datetime(string='Date Order', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_uom = fields.Many2one('product.uom', string='Unit of Measure', readonly=True)
    categ_id = fields.Many2one('product.category',string='Product Category', readonly=True)
    state = fields.Selection([('draft', 'New'), ('paid', 'Closed'), ('done', 'Synchronized'), ('invoiced', 'Invoiced'), ('cancel', 'Cancelled'), ('manual', 'Sale to Invoice')],
            string='Status')
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    price_total = fields.Float(string='Total Price', readonly=True)
    total_discount = fields.Float(string='Total Discount', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    nbr = fields.Integer(string='# of Lines', readonly=True)
    product_qty = fields.Integer(string='Product Quantity', readonly=True)
    delay_validation = fields.Integer(string='Delay Validation')
    type = fields.Selection([('sale','Sale'), ('pos','Pos')], string="Sales Channel")
    picked = fields.Integer(string='Picked', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_so_pos_order')
        cr.execute(""" CREATE OR REPLACE VIEW report_so_pos_order AS (
                SELECT
                    -min(pos_line.id) AS id,
                    count(*) AS nbr,
                    pos_order.date_order AS date,
                    sum(pos_line.qty * uom.factor) AS product_qty,
                    sum(pos_line.qty * pos_line.price_unit) AS price_total,
                    sum((pos_line.qty * pos_line.price_unit) * (pos_line.discount / 100)) AS total_discount,
                    sum(cast(to_char(date_trunc('day',pos_order.date_order) - date_trunc('day',pos_order.create_date),'DD') AS int)) AS delay_validation,
                    pos_order.partner_id AS partner_id,
                    pos_order.state AS state,
                    pos_order.user_id AS user_id,
                    count(pos_order.picking_id) AS picked,
                    pos_order.company_id AS company_id,
                    pos_line.product_id AS product_id,
                    template.uom_id AS product_uom,
                    template.categ_id AS categ_id,
                    (SELECT move.warehouse_id FROM pos_order AS pos, stock_move AS move WHERE pos.location_id = move.location_id AND move.warehouse_id IS NOT NULL GROUP BY move.warehouse_id) AS warehouse_id,
                    'pos' AS type
                        
                FROM pos_order_line AS pos_line
                    LEFT JOIN pos_order pos_order ON (pos_order.id=pos_line.order_id)
                    LEFT JOIN product_product product ON (pos_line.product_id=product.id)
                    LEFT JOIN product_template template ON (product.product_tmpl_id=template.id)
                    LEFT JOIN product_uom uom ON (uom.id=template.uom_id)
                GROUP BY
                    pos_order.date_order, pos_order.partner_id,template.categ_id,pos_order.state,template.uom_id,
                    pos_order.user_id,pos_order.company_id,pos_line.product_id,pos_order.create_date,pos_order.picking_id
                HAVING
                    sum(pos_line.qty * uom.factor) != 0
                UNION ALL
                SELECT
                    min(sale_line.id) AS id,
                    count(*) AS nbr,
                    sale_order.date_order AS date,
                    sum(sale_line.product_uom_qty / uom.factor * template_uom.factor) AS product_qty,
                    sum(sale_line.product_uom_qty * sale_line.price_unit) AS price_total,
                    sum((sale_line.product_uom_qty * sale_line.price_unit) * (sale_line.discount / 100)) AS total_discount,
                    extract(epoch from avg(date_trunc('day',sale_order.date_confirm)-date_trunc('day',sale_order.create_date)))/(24*60*60)::decimal(16,2) AS delay_validation,
                    sale_order.partner_id AS partner_id,
                    sale_order.state AS state,
                    sale_order.user_id AS user_id,
                    sale_order.shipped::integer AS picked,
                    sale_order.company_id AS company_id,
                    sale_line.product_id AS product_id,
                    template.uom_id AS product_uom,
                    template.categ_id AS categ_id,
                    sale_order.warehouse_id AS warehouse_id,
                    'sale' AS type

                FROM sale_order_line AS sale_line
                    LEFT JOIN sale_order sale_order ON (sale_order.id=sale_line.order_id)
                    LEFT JOIN product_product product ON (sale_line.product_id=product.id)
                    LEFT JOIN product_template template ON (product.product_tmpl_id=template.id)
                    LEFT JOIN product_uom uom ON (uom.id=sale_line.product_uom)
                    LEFT JOIN product_uom template_uom ON (template_uom.id=template.uom_id)
                GROUP BY
                    sale_order.date_order,sale_order.partner_id,template.categ_id,sale_order.state,template.uom_id,
                    sale_order.user_id,sale_order.company_id,sale_line.product_id,sale_order.shipped,sale_order.warehouse_id
                    )""")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
