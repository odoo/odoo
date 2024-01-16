# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_product_expiry = fields.Boolean("Expiration Dates",
        help="Track following dates on lots & serial numbers: best before, removal, end of life, alert. \n Such dates are set automatically at lot/serial number creation based on values set on the product (in days).")
    group_stock_production_lot = fields.Boolean("Lots & Serial Numbers",
        implied_group='stock.group_production_lot')
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
    stock_move_email_validation = fields.Boolean(related='company_id.stock_move_email_validation', readonly=False)
    stock_mail_confirmation_template_id = fields.Many2one(related='company_id.stock_mail_confirmation_template_id', readonly=False)
    module_stock_sms = fields.Boolean("SMS Confirmation")
    module_delivery = fields.Boolean("Delivery Methods")
    module_delivery_dhl = fields.Boolean("DHL Express Connector")
    module_delivery_fedex = fields.Boolean("FedEx Connector")
    module_delivery_ups = fields.Boolean("UPS Connector")
    module_delivery_usps = fields.Boolean("USPS Connector")
    module_delivery_bpost = fields.Boolean("bpost Connector")
    module_delivery_easypost = fields.Boolean("Easypost Connector")
    module_quality_control = fields.Boolean("Quality")
    module_quality_control_worksheet = fields.Boolean("Quality Worksheet")
    group_stock_multi_locations = fields.Boolean('Storage Locations', implied_group='stock.group_stock_multi_locations',
        help="Store products in specific locations of your warehouse (e.g. bins, racks) and to track inventory accordingly.")
    group_stock_storage_categories = fields.Boolean(
        'Storage Categories', implied_group='stock.group_stock_storage_categories')
    annual_inventory_month = fields.Selection(related='company_id.annual_inventory_month', readonly=False)
    annual_inventory_day = fields.Integer(related='company_id.annual_inventory_day', readonly=False)
    group_stock_reception_report = fields.Boolean("Reception Report", implied_group='stock.group_reception_report')
    group_stock_auto_reception_report = fields.Boolean("Show Reception Report at Validation", implied_group='stock.group_auto_reception_report')

    @api.onchange('group_stock_multi_locations')
    def _onchange_group_stock_multi_locations(self):
        if not self.group_stock_multi_locations:
            self.group_stock_adv_location = False
            self.group_stock_storage_categories = False

    @api.onchange('group_stock_production_lot')
    def _onchange_group_stock_production_lot(self):
        if not self.group_stock_production_lot:
            self.group_lot_on_delivery_slip = False

    @api.onchange('group_stock_adv_location')
    def onchange_adv_location(self):
        if self.group_stock_adv_location and not self.group_stock_multi_locations:
            self.group_stock_multi_locations = True

    def set_values(self):
        warehouse_grp = self.env.ref('stock.group_stock_multi_warehouses')
        location_grp = self.env.ref('stock.group_stock_multi_locations')
        base_user = self.env.ref('base.group_user')
        if not self.group_stock_multi_locations and location_grp in base_user.implied_ids and warehouse_grp in base_user.implied_ids:
            raise UserError(_("You can't desactivate the multi-location if you have more than once warehouse by company"))

        # Deactivate putaway rules with storage category when not in storage category
        # group. Otherwise, active them.
        storage_cate_grp = self.env.ref('stock.group_stock_storage_categories')
        PutawayRule = self.env['stock.putaway.rule']
        if self.group_stock_storage_categories and storage_cate_grp not in base_user.implied_ids:
            putaway_rules = PutawayRule.search([
                ('active', '=', False),
                ('storage_category_id', '!=', False)
            ])
            putaway_rules.write({'active': True})
        elif not self.group_stock_storage_categories and storage_cate_grp in base_user.implied_ids:
            putaway_rules = PutawayRule.search([('storage_category_id', '!=', False)])
            putaway_rules.write({'active': False})

        previous_group = self.default_get(['group_stock_multi_locations', 'group_stock_production_lot', 'group_stock_tracking_lot'])
        was_operations_showed = self.env['stock.picking.type'].with_user(SUPERUSER_ID)._default_show_operations()
        res = super(ResConfigSettings, self).set_values()

        if not self.user_has_groups('stock.group_stock_manager'):
            return

        # If we just enabled multiple locations with this settings change, we can deactivate
        # the internal operation types of the warehouses, so they won't appear in the dashboard.
        # Otherwise (if we just disabled multiple locations with this settings change), activate them
        warehouse_obj = self.env['stock.warehouse']
        if self.group_stock_multi_locations and not previous_group.get('group_stock_multi_locations'):
            # override active_test that is false in set_values
            warehouse_obj.with_context(active_test=True).search([]).mapped('int_type_id').write({'active': True})
        elif not self.group_stock_multi_locations and previous_group.get('group_stock_multi_locations'):
            warehouse_obj.search([
                ('reception_steps', '=', 'one_step'),
                ('delivery_steps', '=', 'ship_only')]
            ).mapped('int_type_id').write({'active': False})

        if not was_operations_showed and self.env['stock.picking.type'].with_user(SUPERUSER_ID)._default_show_operations():
            picking_types = self.env['stock.picking.type'].with_context(active_test=False).search([
                ('code', '!=', 'incoming'),
                ('show_operations', '=', False)
            ])
            picking_types.sudo().write({'show_operations': True})
        if not self.group_stock_production_lot and previous_group.get('group_stock_production_lot'):
            if self.env['product.product'].search_count([('tracking', '!=', 'none')]):
                raise UserError(_("You have product(s) in stock that have lot/serial number tracking enabled. \nSwitch off tracking on all the products before switching off this setting."))

        return res
