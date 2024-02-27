# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_product_expiry = fields.Boolean("Expiration Dates",
        help="Track following dates on lots & serial numbers: best before, removal, end of life, alert. \n Such dates are set automatically at lot/serial number creation based on values set on the product (in days).")
    group_stock_production_lot = fields.Boolean("Lots & Serial Numbers",
        implied_group='stock.group_production_lot', group="base.group_user,base.group_portal")
    group_stock_lot_print_gs1 = fields.Boolean("Print GS1 Barcodes for Lots & Serial Numbers",
        implied_group='stock.group_stock_lot_print_gs1')
    group_lot_on_delivery_slip = fields.Boolean("Display Lots & Serial Numbers on Delivery Slips",
        implied_group='stock.group_lot_on_delivery_slip', group="base.group_user,base.group_portal")
    group_stock_tracking_lot = fields.Boolean("Packages",
        implied_group='stock.group_tracking_lot')
    group_stock_tracking_owner = fields.Boolean("Consignment",
        implied_group='stock.group_tracking_owner')
    group_stock_adv_location = fields.Boolean("Multi-Step Routes",
        implied_group='stock.group_adv_location',
        help="Add and customize route operations to process product moves in your warehouse(s): e.g. unload > quality control > stock for incoming products, pick > pack > ship for outgoing products. \n You can also set putaway strategies on warehouse locations in order to send incoming products into specific child locations straight away (e.g. specific bins, racks).")
    group_warning_stock = fields.Boolean("Warnings for Stock", implied_group='stock.group_warning_stock')
    group_stock_sign_delivery = fields.Boolean("Signature", implied_group='stock.group_stock_sign_delivery')
    module_stock_picking_batch = fields.Boolean("Batch Transfers")
    group_stock_picking_wave = fields.Boolean('Wave Transfers', implied_group='stock.group_stock_picking_wave',
        help="Group your move operations in wave transfer to process them together")
    module_stock_barcode = fields.Boolean("Barcode Scanner")
    module_stock_barcode_barcodelookup = fields.Boolean("Stock Barcode Database")
    stock_move_email_validation = fields.Boolean(related='company_id.stock_move_email_validation', readonly=False)
    module_stock_sms = fields.Boolean("SMS Confirmation")
    module_delivery = fields.Boolean("Delivery Methods")
    module_delivery_dhl = fields.Boolean("DHL Express Connector")
    module_delivery_fedex = fields.Boolean("FedEx Connector")
    module_delivery_ups = fields.Boolean("UPS Connector")
    module_delivery_usps = fields.Boolean("USPS Connector")
    module_delivery_bpost = fields.Boolean("bpost Connector")
    module_delivery_easypost = fields.Boolean("Easypost Connector")
    module_delivery_sendcloud = fields.Boolean("Sendcloud Connector")
    module_delivery_shiprocket = fields.Boolean("Shiprocket Connector")
    module_delivery_starshipit = fields.Boolean("Starshipit Connector")
    module_quality_control = fields.Boolean("Quality")
    module_quality_control_worksheet = fields.Boolean("Quality Worksheet")
    group_stock_multi_locations = fields.Boolean('Storage Locations', implied_group='stock.group_stock_multi_locations',
        help="Store products in specific locations of your warehouse (e.g. bins, racks) and to track inventory accordingly.")
    annual_inventory_month = fields.Selection(related='company_id.annual_inventory_month', readonly=False)
    annual_inventory_day = fields.Integer(related='company_id.annual_inventory_day', readonly=False)
    group_stock_reception_report = fields.Boolean("Reception Report", implied_group='stock.group_reception_report')
    module_stock_dropshipping = fields.Boolean("Dropshipping")
    barcode_separator = fields.Char(
        "Separator", config_parameter='stock.barcode_separator',
        help="Character(s) used to separate data contained within an aggregate barcode (i.e. a barcode containing multiple barcode encodings)")
    module_stock_transport = fields.Boolean("Dispatch Management System")

    @api.onchange('group_stock_multi_locations')
    def _onchange_group_stock_multi_locations(self):
        if not self.group_stock_multi_locations:
            self.group_stock_adv_location = False

    @api.onchange('group_stock_production_lot')
    def _onchange_group_stock_production_lot(self):
        if not self.group_stock_production_lot:
            self.group_lot_on_delivery_slip = False
            self.module_product_expiry = False

    @api.onchange('group_stock_adv_location')
    def onchange_adv_location(self):
        if self.group_stock_adv_location and not self.group_stock_multi_locations:
            self.group_stock_multi_locations = True

    def set_values(self):
        warehouse_grp = self.env.ref('stock.group_stock_multi_warehouses')
        location_grp = self.env.ref('stock.group_stock_multi_locations')
        base_user = self.env.ref('base.group_user')
        base_user_implied_ids = base_user.implied_ids
        if not self.group_stock_multi_locations and location_grp in base_user_implied_ids and warehouse_grp in base_user_implied_ids:
            raise UserError(_("You can't deactivate the multi-location if you have more than once warehouse by company"))

        previous_group = self.default_get(['group_stock_multi_locations', 'group_stock_production_lot', 'group_stock_tracking_lot'])
        super().set_values()

        if not self.env.user.has_group('stock.group_stock_manager'):
            return

        # If we just enabled multiple locations with this settings change, we can deactivate
        # the internal operation types of the warehouses, so they won't appear in the dashboard.
        # Otherwise (if we just disabled multiple locations with this settings change), activate them
        warehouse_obj = self.env['stock.warehouse']
        if self.group_stock_multi_locations and not previous_group.get('group_stock_multi_locations'):
            # override active_test that is false in set_values
            warehouse_obj.with_context(active_test=True).search([]).int_type_id.active = True
            # Disable the views removing the create button from the location list and form.
            # Be resilient if the views have been deleted manually.
            for view in (
                self.env.ref('stock.stock_location_view_tree2_editable', raise_if_not_found=False),
                self.env.ref('stock.stock_location_view_form_editable', raise_if_not_found=False),
            ):
                if view:
                    view.active = False
        elif not self.group_stock_multi_locations and previous_group.get('group_stock_multi_locations'):
            warehouse_obj.search([
                ('reception_steps', '=', 'one_step'),
                ('delivery_steps', '=', 'ship_only')
            ]).int_type_id.active = False
            # Enable the views removing the create button from the location list and form.
            # Be resilient if the views have been deleted manually.
            for view in (
                self.env.ref('stock.stock_location_view_tree2_editable', raise_if_not_found=False),
                self.env.ref('stock.stock_location_view_form_editable', raise_if_not_found=False),
            ):
                if view:
                    view.active = True

        if not self.group_stock_production_lot and previous_group.get('group_stock_production_lot'):
            if self.env['product.product'].search_count([('tracking', '!=', 'none')], limit=1):
                raise UserError(_("You have product(s) in stock that have lot/serial number tracking enabled. \nSwitch off tracking on all the products before switching off this setting."))

        return
