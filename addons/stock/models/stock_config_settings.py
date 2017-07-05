# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockConfigSettings(models.TransientModel):
    _name = 'stock.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.user.company_id, required=True)
    module_procurement_jit = fields.Selection([
        (1, 'Immediately after sales order confirmation'),
        (0, 'Manually or based on automatic scheduler')
        ], "Reservation",
        help="Reserving products manually in delivery orders or by running the scheduler is advised to better manage priorities in case of long customer lead times or/and frequent stock-outs.")
    module_product_expiry = fields.Boolean("Expiration Dates",
        help="Track following dates on lots & serial numbers: best before, removal, end of life, alert. \n Such dates are set automatically at lot/serial number creation based on values set on the product (in days).")
    group_stock_packaging = fields.Boolean('Product Packages',
        implied_group='product.group_stock_packaging')
    group_stock_production_lot = fields.Boolean("Lots & Serial Numbers",
        implied_group='stock.group_production_lot')
    group_stock_tracking_lot = fields.Boolean("Delivery Packages",
        implied_group='stock.group_tracking_lot')
    group_stock_tracking_owner = fields.Boolean("Consignment",
        implied_group='stock.group_tracking_owner')
    group_stock_adv_location = fields.Boolean("Multi-Step Routes",
        implied_group='stock.group_adv_location',
        help="Add and customize route operations to process product moves in your warehouse(s): e.g. unload > quality control > stock for incoming products, pick > pack > ship for outgoing products. \n You can also set putaway strategies on warehouse locations in order to send incoming products into specific child locations straight away (e.g. specific bins, racks).")
    group_warning_stock = fields.Boolean("Warnings", implied_group='stock.group_warning_stock')
    propagation_minimum_delta = fields.Integer(related='company_id.propagation_minimum_delta', string="No Rescheduling Propagation")
    use_propagation_minimum_delta = fields.Boolean(
        string="No Rescheduling Propagation",
        oldname='default_new_propagation_minimum_delta',
        help="Rescheduling applies to any chain of operations (e.g. Make To Order, Pick Pack Ship). In the case of MTO sales, a vendor delay (updated incoming date) impacts the expected delivery date to the customer. \n This option allows to not propagate the rescheduling if the change is not critical.")
    module_stock_picking_wave = fields.Boolean("Picking Waves")
    module_stock_calendar = fields.Boolean("Vendor Calendar for Reordering",
        help='Scheduled dates of requests for quotation generated from reordering rules are based on vendor lead times (defined on products).\nBy default, such a scheduling is made on calendar days. This option allow to adapt the scheduling with vendor calendars to set on reordering rules.')
    module_stock_barcode = fields.Boolean("Barcode Scanner")
    module_delivery_dhl = fields.Boolean("DHL")
    module_delivery_fedex = fields.Boolean("FedEx")
    module_delivery_ups = fields.Boolean("UPS")
    module_delivery_usps = fields.Boolean("USPS")
    module_delivery_bpost = fields.Boolean("bpost")
    group_uom = fields.Boolean("Units of Measure", implied_group='product.group_uom')
    group_product_variant = fields.Boolean("Attributes & Variants", implied_group='product.group_product_variant')
    group_stock_multi_locations = fields.Boolean('Storage Locations', implied_group='stock.group_stock_multi_locations',
        help="Store products in specific locations of your warehouse (e.g. bins, racks) and to track inventory accordingly.")
    group_stock_multi_warehouses = fields.Boolean('Multi-Warehouses', implied_group='stock.group_stock_multi_warehouses')
    module_quality = fields.Boolean(string="Quality Control")
    module_mrp = fields.Boolean(string="Manufacturing")
    module_sale = fields.Boolean(string="Sales")
    module_purchase = fields.Boolean(string="Purchase")

    @api.onchange('use_propagation_minimum_delta')
    def _onchange_use_propagation_minimum_delta(self):
        if not self.use_propagation_minimum_delta:
            self.propagation_minimum_delta = 1

    @api.onchange('group_stock_multi_locations')
    def _onchange_group_stock_multi_locations(self):
        if not self.group_stock_multi_locations:
            self.group_stock_multi_warehouses = False
            self.group_stock_adv_location = False

    @api.onchange('group_stock_multi_warehouses')
    def _onchange_group_stock_multi_warehouses(self):
        if self.group_stock_multi_warehouses:
            self.group_stock_multi_locations = True

    @api.onchange('group_stock_adv_location')
    def onchange_adv_location(self):
        if self.group_stock_adv_location and not self.group_stock_multi_locations:
            self.group_stock_multi_locations = True

    @api.model
    def get_values(self):
        res = super(StockConfigSettings, self).get_values()
        res.update(
            use_propagation_minimum_delta=self.env['ir.config_parameter'].sudo().get_param('stock.use_propagation_minimum_delta')
        )
        return res

    @api.multi
    def set_values(self):
        super(StockConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('stock.use_propagation_minimum_delta', self.use_propagation_minimum_delta)
        """ If we are not in multiple locations, we can deactivate the internal
        operation types of the warehouses, so they won't appear in the dashboard.
        Otherwise, activate them.
        """
        if self.group_stock_multi_locations:
            warehouses = self.env['stock.warehouse'].search([])
            active = True
        else:
            warehouses = self.env['stock.warehouse'].search([
                ('reception_steps', '=', 'one_step'),
                ('delivery_steps', '=', 'ship_only')])
            active = False
        warehouses.mapped('int_type_id').write({'active': active})
