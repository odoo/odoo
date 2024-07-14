# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class StockReport(models.Model):
    _name = 'stock.report'
    _description = "Stock Report"
    _rec_name = 'id'
    _auto = False

    id = fields.Integer("", readonly=True)
    date_done = fields.Datetime("Transfer Date", readonly=True)
    creation_date = fields.Datetime("Creation Date", readonly=True)
    scheduled_date = fields.Datetime("Expected Date", readonly=True)
    delay = fields.Float("Delay (Days)", readonly=True, group_operator="avg")
    cycle_time = fields.Float("Cycle Time (Days)", readonly=True, group_operator="avg")
    picking_type_code = fields.Selection([
        ('incoming', 'Vendors'),
        ('outgoing', 'Customers'),
        ('internal', 'Internal')], string="Type", readonly=True)
    operation_type = fields.Char("Operation Type", readonly=True, translate=True)
    operation_type_id = fields.Many2one('stock.picking.type', string='Operation', readonly=True)
    product_id = fields.Many2one('product.product', "Product", readonly=True)
    picking_name = fields.Char("Picking Name", readonly=True)
    reference = fields.Char("Reference", readonly=True)
    picking_id = fields.Many2one('stock.picking', 'Transfer Reference', readonly=True)
    state = fields.Selection([
        ('draft', 'New'), ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Move'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'),
        ('done', 'Done')], string='Status', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    is_backorder = fields.Boolean("Is a Backorder", readonly=True)
    product_qty = fields.Float("Product Quantity", readonly=True)
    is_late = fields.Boolean("Is Late", readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)

    @api.depends('reference', 'product_id.name')
    def _compute_display_name(self):
        for report in self:
            report.display_name = f'{report.reference} - {report.product_id.display_name}'

    def _select(self):
        select_str = """
            sm.id as id,
            sp.name as picking_name,
            sp.date_done as date_done,
            sp.creation_date as creation_date,
            sp.scheduled_date as scheduled_date,
            sp.partner_id as partner_id,
            sp.is_backorder as is_backorder,
            sp.delay as delay,
            sp.delay > 0 as is_late,
            sp.cycle_time as cycle_time,
            spt.code as picking_type_code,
            spt.name as operation_type,
            spt.id as operation_type_id,
            p.id as product_id,
            sm.reference as reference,
            sm.picking_id as picking_id,
            sm.state as state,
            sm.product_qty as product_qty,
            sm.company_id as company_id,
            cat.id as categ_id
        """

        return select_str

    def _from(self):
        from_str = """
            stock_move sm
            LEFT JOIN (
                SELECT
                    id,
                    name,
                    date_done,
                    date as creation_date,
                    scheduled_date,
                    partner_id,
                    backorder_id IS NOT NULL as is_backorder,
                    (extract(epoch from avg(date_done-scheduled_date))/(24*60*60))::decimal(16,2) as delay,
                    (extract(epoch from avg(date_done-date))/(24*60*60))::decimal(16,2) as cycle_time
                FROM
                    stock_picking
                GROUP BY
                    id,
                    name,
                    date_done,
                    date,
                    scheduled_date,
                    partner_id,
                    is_backorder
            ) sp ON sm.picking_id = sp.id
            LEFT JOIN stock_picking_type spt ON sm.picking_type_id = spt.id
            INNER JOIN product_product p ON sm.product_id = p.id
            INNER JOIN product_template t ON p.product_tmpl_id = t.id
            INNER JOIN product_category cat ON t.categ_id = cat.id
            WHERE t.type = 'product'
        """

        return from_str

    def _group_by(self):
        group_by_str = """
            sm.id,
            sm.reference,
            sm.picking_id,
            sm.state,
            sm.product_qty,
            sm.company_id,
            sp.name,
            sp.date_done,
            sp.creation_date,
            sp.scheduled_date,
            sp.partner_id,
            sp.is_backorder,
            sp.delay,
            sp.cycle_time,
            spt.code,
            spt.name,
            spt.id,
            p.id,
            is_late,
            cat.id
        """

        return group_by_str

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
                            SELECT
                                %s
                            FROM
                                %s
                            GROUP BY
                                %s
            )""" % (self._table, self._select(), self._from(), self._group_by(),))
