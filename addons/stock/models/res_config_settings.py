# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_procurement_jit = fields.Selection([
        ('1', 'Immediately after sales order confirmation'),
        ('0', 'Manually or based on automatic scheduler')
        ], "Reservation", default='0',
        help="Reserving products manually in delivery orders or by running the scheduler is advised to better manage priorities in case of long customer lead times or/and frequent stock-outs.")
    module_product_expiry = fields.Boolean("Expiration Dates",
        help="Track following dates on lots & serial numbers: best before, removal, end of life, alert. \n Such dates are set automatically at lot/serial number creation based on values set on the product (in days).")
    group_stock_production_lot = fields.Boolean("Lots & Serial Numbers",
        implied_group='stock.group_production_lot')
    group_lot_on_delivery_slip = fields.Boolean("Display Lots & Serial Numbers on Delivery Slips",
        implied_group='stock.group_lot_on_delivery_slip')
    group_stock_tracking_lot = fields.Boolean("Packages",
        implied_group='stock.group_tracking_lot')
    group_stock_tracking_owner = fields.Boolean("Consignment",
        implied_group='stock.group_tracking_owner')
    group_stock_adv_location = fields.Boolean("Multi-Step Routes",
        implied_group='stock.group_adv_location',
        help="Add and customize route operations to process product moves in your warehouse(s): e.g. unload > quality control > stock for incoming products, pick > pack > ship for outgoing products. \n You can also set putaway strategies on warehouse locations in order to send incoming products into specific child locations straight away (e.g. specific bins, racks).")
    group_warning_stock = fields.Boolean("Warnings for Stock", implied_group='stock.group_warning_stock')
    group_stock_sign_delivery = fields.Boolean("Signature", implied_group='stock.group_stock_sign_delivery')
    module_stock_picking_batch = fields.Boolean("Batch Pickings")
    module_stock_barcode = fields.Boolean("Barcode Scanner")
    stock_move_email_validation = fields.Boolean(related='company_id.stock_move_email_validation', readonly=False)
    stock_mail_confirmation_template_id = fields.Many2one(related='company_id.stock_mail_confirmation_template_id', readonly=False)
    module_stock_sms = fields.Boolean("SMS Confirmation")
    module_delivery = fields.Boolean("Delivery Methods")
    module_delivery_dhl = fields.Boolean("DHL USA Connector")
    module_delivery_fedex = fields.Boolean("FedEx Connector")
    module_delivery_ups = fields.Boolean("UPS Connector")
    module_delivery_usps = fields.Boolean("USPS Connector")
    module_delivery_bpost = fields.Boolean("bpost Connector")
    module_delivery_easypost = fields.Boolean("Easypost Connector")
    group_stock_multi_locations = fields.Boolean('Storage Locations', implied_group='stock.group_stock_multi_locations',
        help="Store products in specific locations of your warehouse (e.g. bins, racks) and to track inventory accordingly.")

    @api.onchange('group_stock_multi_locations')
    def _onchange_group_stock_multi_locations(self):
        if not self.group_stock_multi_locations:
            self.group_stock_adv_location = False

    @api.onchange('group_stock_production_lot')
    def _onchange_group_stock_production_lot(self):
        if not self.group_stock_production_lot:
            self.group_lot_on_delivery_slip = False

    @api.onchange('group_stock_adv_location')
    def onchange_adv_location(self):
        if self.group_stock_adv_location and not self.group_stock_multi_locations:
            self.group_stock_multi_locations = True

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()

        if not self.user_has_groups('stock.group_stock_manager'):
            return

        """ If we are not in multiple locations, we can deactivate the internal
        operation types of the warehouses, so they won't appear in the dashboard.
        Otherwise, activate them.
        """
        warehouse_obj = self.env['stock.warehouse']
        if self.group_stock_multi_locations:
            # override active_test that is false in set_values
            warehouses = warehouse_obj.with_context(active_test=True).search([])
            active = True
        else:
            warehouses = warehouse_obj.search([
                ('reception_steps', '=', 'one_step'),
                ('delivery_steps', '=', 'ship_only')])
            active = False
        warehouses.mapped('int_type_id').write({'active': active})

        if self.group_stock_multi_locations or self.group_stock_production_lot or self.group_stock_tracking_lot:
            picking_types = self.env['stock.picking.type'].with_context(active_test=False).search([
                ('code', '!=', 'incoming'),
                ('show_operations', '=', False)
            ])
            picking_types.sudo().write({'show_operations': True})
        return res
