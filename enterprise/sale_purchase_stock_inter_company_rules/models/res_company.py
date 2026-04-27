# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class res_company(models.Model):
    _inherit = 'res.company'

    intercompany_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string="Warehouse",
        help="Default value to set on Purchase(Sales) Orders that will be created based on Sale(Purchase) Orders made to this company",
        compute='_compute_intercompany_stock_fields',
        readonly=False,
        store=True,
    )
    intercompany_sync_delivery_receipt = fields.Boolean(
        string="Synchronize Deliveries to your Receipts",
        default=lambda self: self.env.user.has_group('stock.group_production_lot'),
    )
    intercompany_receipt_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string="Receipt Operation Type",
        help="Default Operation type to set on Receipts that will be created for inter-company transfers",
        compute='_compute_intercompany_stock_fields',
        readonly=False,
        store=True,
    )

    @api.depends('intercompany_generate_sales_orders', 'intercompany_generate_purchase_orders')
    def _compute_intercompany_stock_fields(self):
        stock_warehouse = dict(self.env['stock.warehouse']._read_group(domain=[], groupby=['company_id'], aggregates=['id:recordset']))
        stock_picking_type = dict(self.env['stock.picking.type']._read_group(domain=[('code', '=', 'incoming')], groupby=['company_id'], aggregates=['id:recordset']))
        for company in self:
            if not (company.intercompany_generate_sales_orders or company.intercompany_generate_purchase_orders):
                company.intercompany_warehouse_id = False
                company.intercompany_receipt_type_id = False
            else:
                if not company.intercompany_warehouse_id:
                    company.intercompany_warehouse_id = stock_warehouse.get(company, [False])[0]
                if not company.intercompany_receipt_type_id:
                    company.intercompany_receipt_type_id = stock_picking_type.get(company, [False])[0]
