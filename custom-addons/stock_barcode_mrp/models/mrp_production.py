from odoo import api, fields, models, _


class ManufacturingOrder(models.Model):
    _inherit = 'mrp.production'

    move_raw_line_ids = fields.One2many('stock.move.line', compute='_compute_move_raw_line_ids')
    move_byproduct_line_ids = fields.One2many('stock.move.line', compute='_compute_move_byproduct_line_ids')
    is_completed = fields.Boolean(compute='_compute_is_completed')
    backorder_ids = fields.One2many(related='procurement_group_id.mrp_production_ids')

    @api.depends('move_raw_ids')
    def _compute_move_raw_line_ids(self):
        for order in self:
            order.move_raw_line_ids = order.move_raw_ids.move_line_ids

    @api.depends('move_byproduct_ids')
    def _compute_move_byproduct_line_ids(self):
        for order in self:
            order.move_byproduct_line_ids = order.move_byproduct_ids.move_line_ids

    @api.depends('qty_produced', 'product_qty')
    def _compute_is_completed(self):
        for order in self:
            order.is_completed = order.qty_produced == order.product_qty

    def action_open_barcode_client_action(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock_barcode_mrp.stock_barcode_mo_client_action")
        action = dict(action, target='fullscreen')
        action['context'] = {'active_id': self.id}
        return action

    def set_lot_producing(self):
        """ Special mo barcode action to produce and return SN/lot data compatible with barcode app.
        Helps avoid doing extra db calls within barcode that using action_generate_serial
        would require."""
        self._set_lot_producing()
        action = False
        if self.picking_type_id.auto_print_generated_mrp_lot:
            action = self._autoprint_generated_lot(self.lot_producing_id)
        return self.lot_producing_id.read(self.lot_producing_id._get_fields_stock_barcode(), load=False), action

    def _get_fields_stock_barcode(self):
        return [
            'move_raw_line_ids',
            'move_raw_ids',
            'move_byproduct_line_ids',
            'move_byproduct_ids',
            'production_location_id',
            'picking_type_id',
            'location_src_id',
            'location_dest_id',
            'product_id',
            'product_uom_id',
            'product_qty',
            'qty_producing',
            'lot_producing_id',
            'name',
            'state',
            'picking_type_id',
            'company_id',
            'user_id',
            'procurement_group_id',
            'backorder_ids',
        ]

    def _get_stock_barcode_data(self):
        # Avoid to get the products full name because code and name are separate in the barcode app.
        self = self.with_context(display_default_code=False)
        move_lines = self.move_raw_line_ids | self.move_byproduct_line_ids
        lots = move_lines.lot_id | self.lot_producing_id
        owners = move_lines.owner_id
        # Fetch all implied products in `self`
        products = self.product_id | (self.move_raw_ids + self.move_byproduct_ids).product_id
        moves = self.move_raw_ids | self.move_byproduct_ids
        packagings = products.packaging_ids

        uoms = products.uom_id | move_lines.product_uom_id
        # If UoM setting is active, fetch all UoM's data.
        if self.env.user.has_group('uom.group_uom'):
            uoms |= self.env['uom.uom'].search([])

        # Fetch `stock.location`
        source_locations = self.env['stock.location'].search([('id', 'child_of', self.location_src_id.ids)])
        destination_locations = self.env['stock.location'].search([('id', 'child_of', self.location_dest_id.ids)])
        locations = move_lines.location_id | move_lines.location_dest_id | source_locations | destination_locations | self.production_location_id

        # Fetch `stock.quant.package` and `stock.package.type` if group_tracking_lot.
        packages = self.env['stock.quant.package']
        package_types = self.env['stock.package.type']
        if self.env.user.has_group('stock.group_tracking_lot'):
            packages |= move_lines.package_id | move_lines.result_package_id
            packages |= self.env['stock.quant.package'].with_context(pack_locs=destination_locations.ids)._get_usable_packages()
            package_types = package_types.search([])

        data = {
            "records": {
                "mrp.production": self.read(self._get_fields_stock_barcode(), load=False),
                "stock.picking.type": self.picking_type_id.read(self.picking_type_id._get_fields_stock_barcode(), load=False),
                "stock.move": moves.read(moves._get_fields_stock_barcode(), load=False),
                "stock.move.line": move_lines.read(move_lines._get_fields_stock_barcode(), load=False),
                "product.product": products.read(products._get_fields_stock_barcode(), load=False),
                "product.packaging": packagings.read(packagings._get_fields_stock_barcode(), load=False),
                "res.partner": owners.read(owners._get_fields_stock_barcode(), load=False),
                "stock.location": locations.read(locations._get_fields_stock_barcode(), load=False),
                "stock.package.type": package_types.read(package_types._get_fields_stock_barcode(), False),
                "stock.quant.package": packages.read(packages._get_fields_stock_barcode(), load=False),
                "stock.lot": lots.read(lots._get_fields_stock_barcode(), load=False),
                "uom.uom": uoms.read(uoms._get_fields_stock_barcode(), load=False),
            },
            "nomenclature_id": [self.env.company.nomenclature_id.id],
            "source_location_ids": source_locations.ids,
            "destination_locations_ids": destination_locations.ids,
        }

        data['config'] = self.picking_type_id._get_barcode_config() if self else {}
        data['line_view_id'] = self.env.ref('stock_barcode.stock_move_line_product_selector').id
        data['form_view_id'] = self.env.ref('stock_barcode_mrp.mrp_barcode_form').id
        data['header_view_id'] = self.env.ref('stock_barcode_mrp.mrp_product_selector').id
        data['scrap_view_id'] = self.env.ref('stock_barcode_mrp.scrap_product_selector').id
        data['package_view_id'] = self.env.ref('stock_barcode.stock_quant_barcode_kanban').id
        return data

    @api.model
    def filter_on_barcode(self, barcode):
        """ Searches ready MOs for the scanned product or order.
        """
        barcode_type = None
        nomenclature = self.env.company.nomenclature_id
        if nomenclature.is_gs1_nomenclature:
            parsed_results = nomenclature.parse_barcode(barcode)
            if parsed_results:
                # filter with the last feasible rule
                for result in parsed_results[::-1]:
                    if result['rule'].type in ('product', 'package'):
                        barcode_type = result['rule'].type
                        break

        base_domain = [
            ('state', 'in', ['confirmed', 'progress']),
            ('reservation_state', '=', 'assigned'),
        ]

        active_id = self.env.context.get('active_id')
        additional_context = {
            'search_default_filter_confirmed': 1,
            'search_default_filter_ready': 1,
            'search_default_filter_in_progress': 1,
            'search_default_filter_to_close': 1,
            'search_default_todo': 1,
            'active_id': active_id,
        }
        picking_type = self.env['stock.picking.type'].browse(active_id)
        mo_nums = 0
        if barcode_type == 'product' or not barcode_type:
            product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
            if product:
                mo_nums = self.search_count(base_domain + [('product_id', '=', product.id)])
                if mo_nums:
                    additional_context['search_default_product_id'] = product.id
                else:
                    mo_nums = self.search_count(base_domain + [('move_raw_ids.product_id', '=', product.id)])
                    additional_context['search_default_move_raw_ids'] = barcode
        if not barcode_type and not mo_nums:  # Nothing found yet, try to find picking by name.
            mo_nums = self.search_count(base_domain + [('name', '=', barcode)])
            additional_context['search_default_name'] = barcode

        if not mo_nums:
            if barcode_type:
                return {
                    'warning': {
                        'message': _("No Manufacturing Order ready for this %(barcode_type)s", barcode_type=barcode_type),
                    }
                }
            return {
                'warning': {
                    'title': _('No product or order found for barcode %s', barcode),
                    'message': _('Scan a product to filter the orders.'),
                }
            }

        action = picking_type._get_action('stock_barcode_mrp.mrp_action_kanban')
        action['context'].update(additional_context)
        return {'action': action}
