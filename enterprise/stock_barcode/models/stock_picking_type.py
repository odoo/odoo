from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    barcode_allow_extra_product = fields.Boolean(
        "Allow extra products", default=True,
        help="For planned transfers, allow to add non-reserved products"
    )
    barcode_validation_after_dest_location = fields.Boolean("Force a destination on all products")
    barcode_validation_all_product_packed = fields.Boolean("Force all products to be packed")
    barcode_validation_full = fields.Boolean(
        "Allow full picking validation", default=True,
        help="Allow to validate a picking even if nothing was scanned yet (and so, do an immediate transfert)")
    restrict_scan_product = fields.Boolean(
        "Force Product scan?", help="Line's product must be scanned before the line can be edited")
    restrict_put_in_pack = fields.Selection(
        [
            ('mandatory', "After each product"),
            ('optional', "After group of Products"),
            ('no', "No"),
        ], "Force put in pack?",
        help="Does the picker have to put in a package the scanned products? If yes, at which rate?",
        default="optional", required=True)
    restrict_scan_tracking_number = fields.Selection(
        [
            ('mandatory', "Mandatory Scan"),
            ('optional', "Optional Scan"),
        ], "Force Lot/Serial scan?", default='optional', required=True)
    restrict_scan_source_location = fields.Selection(
        [
            ('no', "No Scan"),
            ('mandatory', "Mandatory Scan"),
        ], "Force Source Location scan?", default='no', required=True)
    restrict_scan_dest_location = fields.Selection(
        [
            ('mandatory', "After each product"),
            ('optional', "After group of Products"),
            ('no', "No"),
        ], "Force Destination Location scan?",
        help="Does the picker have to scan the destination? If yes, at which rate?",
        default='optional', required=True)
    show_barcode_validation = fields.Boolean(
        compute='_compute_show_barcode_validation',
        help='Technical field used to compute whether the "Final Validation" group should be displayed, solving combined groups/invisible complexity.')
    show_reserved_sns = fields.Boolean(
        "Show reserved lots/SN", help="Allows to display reserved lots/serial numbers. "
        "When non active, it is clear for the picker that they can pick the lots/serials they want.")
    is_barcode_picking_type = fields.Boolean(
        compute='_compute_is_barcode_picking_type',
        help="Technical field indicating if should be used in barcode app and used to control visibility in the related UI.")

    @api.depends('restrict_scan_product', 'restrict_put_in_pack', 'restrict_scan_dest_location')
    def _compute_show_barcode_validation(self):
        for picking_type in self:
            # reflect all fields invisible conditions
            hide_full = picking_type.restrict_scan_product
            hide_all_product_packed = not self.env.user.has_group('stock.group_tracking_lot') or\
                                      picking_type.restrict_put_in_pack != 'optional'
            hide_dest_location = not self.env.user.has_group('stock.group_stock_multi_locations') or\
                                 (picking_type.code == 'outgoing' or picking_type.restrict_scan_dest_location != 'optional')
            # show if not all hidden
            picking_type.show_barcode_validation = not (hide_full and hide_all_product_packed and hide_dest_location)

    @api.depends('code')
    def _compute_is_barcode_picking_type(self):
        for picking_type in self:
            if picking_type.code in ['incoming', 'outgoing', 'internal']:
                picking_type.is_barcode_picking_type = True
            else:
                picking_type.is_barcode_picking_type = False

    @api.constrains('restrict_scan_source_location', 'restrict_scan_dest_location')
    def _check_restrinct_scan_locations(self):
        for picking_type in self:
            if picking_type.code == 'internal' and\
               picking_type.restrict_scan_dest_location == 'optional' and\
               picking_type.restrict_scan_source_location == 'mandatory':
                raise UserError(_("If the source location must be scanned, then the destination location must either be scanned after each product or not scanned at all."))

    def get_action_picking_tree_ready_kanban(self):
        return self._get_action('stock_barcode.stock_picking_action_kanban')

    def _get_barcode_config(self):
        self.ensure_one()
        # Defines if all lines need to be packed to be able to validate a transfer.
        locations_enable = self.env.user.has_group('stock.group_stock_multi_locations')
        lines_need_to_be_packed = self.env.user.has_group('stock.group_tracking_lot') and (
            self.restrict_put_in_pack == 'mandatory' or (
                self.restrict_put_in_pack == 'optional'
                and self.barcode_validation_all_product_packed
            )
        )
        config = {
            # Boolean fields.
            'barcode_allow_extra_product': self.barcode_allow_extra_product,
            'barcode_validation_after_dest_location': self.barcode_validation_after_dest_location,
            'barcode_validation_all_product_packed': self.barcode_validation_all_product_packed,
            'barcode_validation_full': not self.restrict_scan_product and self.barcode_validation_full,  # Forced to be False when scanning a product is mandatory.
            'create_backorder': self.create_backorder,
            'restrict_scan_product': self.restrict_scan_product,
            # Selection fields converted into boolean.
            'restrict_scan_tracking_number': self.restrict_scan_tracking_number == 'mandatory',
            'restrict_scan_source_location': locations_enable and self.restrict_scan_source_location == 'mandatory',
            # Selection fields.
            'restrict_put_in_pack': self.restrict_put_in_pack,
            'restrict_scan_dest_location': self.restrict_scan_dest_location if locations_enable else 'no',
            # Additional parameters.
            'lines_need_to_be_packed': lines_need_to_be_packed,
        }
        return config

    def _get_fields_stock_barcode(self):
        return [
            'default_location_dest_id',
            'default_location_src_id',
            'use_create_lots',
            'use_existing_lots',
            'show_reserved_sns',
        ]
