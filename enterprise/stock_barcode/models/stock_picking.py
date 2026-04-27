# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.tools import html2plaintext, is_html_empty
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _barcode_field = 'name'

    def action_cancel_from_barcode(self):
        self.ensure_one()
        view = self.env.ref('stock_barcode.stock_barcode_cancel_operation_view')
        return {
            'name': _('Cancel this operation?'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock_barcode.cancel.operation',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': dict(self.env.context, default_picking_id=self.id),
        }

    @api.model
    def action_open_new_picking(self):
        """ Creates a new picking of the current picking type and open it.

        :return: the action used to open the picking, or false
        :rtype: dict
        """
        context = self.env.context
        if context.get('active_model') == 'stock.picking.type':
            picking_type = self.env['stock.picking.type'].browse(context.get('active_id'))
            if picking_type.exists():
                new_picking = self._create_new_picking(picking_type)
                return new_picking.action_open_picking_client_action()
        return False

    def action_open_picking(self):
        """ method to open the form view of the current record
        from a button on the kanban view
        """
        self.ensure_one()
        view_id = self.env.ref('stock.view_picking_form').id
        return {
            'name': _('Open picking form'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
        }

    def action_open_picking_client_action(self):
        """ method to open the form view of the current record
        from a button on the kanban view
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock_barcode.stock_barcode_picking_client_action")
        context = {'active_id': self.id}
        return dict(action, context=context)

    def action_create_return_picking(self):
        """
        Create a return picking for the current picking and open it in the barcode app
        """
        self.ensure_one()
        return_picking = self.with_context(active_model='stock.picking', active_id=self.id).env['stock.return.picking'].create({})
        for line in return_picking.product_return_moves:
            line.quantity = line.move_id.quantity
        new_picking = return_picking._create_return()
        return new_picking.action_open_picking_client_action()

    def action_print_barcode(self):
        return self.action_open_label_type()

    def action_print_delivery_slip(self):
        return self.env.ref('stock.action_report_delivery').report_action(self)

    def action_print_packges(self):
        return self.env.ref('stock.action_report_picking_packages').report_action(self)

    def _get_stock_barcode_data(self):
        # Avoid to get the products full name because code and name are separate in the barcode app.
        self = self.with_context(display_default_code=False)
        move_lines = self.move_line_ids
        lots = move_lines.lot_id
        partners = move_lines.owner_id | self.partner_id
        # Fetch all implied products in `self` and adds last used products to avoid additional rpc.
        products = self.move_ids.product_id | move_lines.product_id
        packagings = products.packaging_ids

        uoms = products.uom_id | move_lines.product_uom_id
        # If UoM setting is active, fetch all UoM's data.
        if self.env.user.has_group('uom.group_uom'):
            uoms |= self.env['uom.uom'].search([])

        # Fetch `stock.location`
        source_locations = self.env['stock.location'].search([('id', 'child_of', self.location_id.ids)])
        destination_locations = self.env['stock.location'].search([('id', 'child_of', self.location_dest_id.ids)])
        package_locations = self.env['stock.location'].search([('id', 'child_of', self.location_dest_id.ids), ('usage', '!=', 'customer')])
        locations = self.location_id | self.location_dest_id |  move_lines.location_id | move_lines.location_dest_id | source_locations | destination_locations

        # Fetch `stock.quant.package` and `stock.package.type` if group_tracking_lot.
        packages = self.env['stock.quant.package']
        package_types = self.env['stock.package.type']
        if self.env.user.has_group('stock.group_tracking_lot'):
            packages |= move_lines.package_id | move_lines.result_package_id
            packages |= self.env['stock.quant.package'].with_context(pack_locs=package_locations.ids)._get_usable_packages()
            package_types = package_types.search([])

        data = {
            "records": {
                "stock.picking": self.read(self._get_fields_stock_barcode(), load=False),
                "stock.picking.type": self.picking_type_id.read(self.picking_type_id._get_fields_stock_barcode(), load=False),
                "stock.move": self.move_ids.read(self.move_ids._get_fields_stock_barcode(), load=False),
                "stock.move.line": move_lines.read(move_lines._get_fields_stock_barcode(), load=False),
                # `self` can be a record set (e.g.: a picking batch), set only the first partner in the context.
                "product.product": products.with_context(partner_id=self[:1].partner_id.id).read(products._get_fields_stock_barcode(), load=False),
                "product.packaging": packagings.read(packagings._get_fields_stock_barcode(), load=False),
                "res.partner": partners.read(partners._get_fields_stock_barcode(), load=False),
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
        # Extracts pickings' note if it's empty HTML.
        for picking in data['records']['stock.picking']:
            picking['note'] = False if is_html_empty(picking['note']) else html2plaintext(picking['note'])

        data['config'] = self.picking_type_id._get_barcode_config()
        if self._should_ignore_backorders():
            data['config']['create_backorder'] = 'never'
        data['line_view_id'] = self.env.ref('stock_barcode.stock_move_line_product_selector').id
        data['form_view_id'] = self.env.ref('stock_barcode.stock_picking_barcode').id
        data['scrap_view_id'] = self.env.ref('stock_barcode.scrap_product_selector').id
        data['package_view_id'] = self.env.ref('stock_barcode.stock_quant_barcode_kanban').id
        return data

    @api.model
    def _create_new_picking(self, picking_type):
        """ Create a new picking for the given picking type.

        :param picking_type:
        :type picking_type: :class:`~odoo.addons.stock.models.stock_picking.PickingType`
        :return: a new picking
        :rtype: :class:`~odoo.addons.stock.models.stock_picking.Picking`
        """
        # Find source and destination Locations
        location_dest_id, location_id = picking_type.warehouse_id._get_partner_locations()
        if picking_type.default_location_src_id:
            location_id = picking_type.default_location_src_id
        if picking_type.default_location_dest_id:
            location_dest_id = picking_type.default_location_dest_id

        # Create and confirm the picking
        return self.env['stock.picking'].create({
            'user_id': False,
            'picking_type_id': picking_type.id,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
        })

    def _get_fields_stock_barcode(self):
        """ List of fields on the stock.picking object that are needed by the
        client action. The purpose of this function is to be overridden in order
        to inject new fields to the client action.
        """
        return [
            'company_id',
            'location_dest_id',
            'location_id',
            'move_ids',
            'move_line_ids',
            'name',
            'note',
            'partner_id',
            'picking_type_code',
            'picking_type_entire_packs',
            'picking_type_id',
            'return_id',
            'signature',
            'state',
            'use_create_lots',
            'use_existing_lots',
            'user_id',
        ]

    @api.model
    def filter_on_barcode(self, barcode):
        """ Searches ready pickings for the scanned product/package/lot.
        """
        barcode_type = None
        nomenclature = self.env.company.nomenclature_id
        if nomenclature.is_gs1_nomenclature:
            try:
                parsed_results = nomenclature.parse_barcode(barcode)
            except ValidationError:
                parsed_results = False
            if parsed_results:
                # filter with the last feasible rule
                for result in parsed_results[::-1]:
                    if result['type'] in ('product', 'package', 'lot'):
                        barcode_type = result['type']
                        break

        active_id = self.env.context.get('active_id')
        picking_type = self.env['stock.picking.type'].browse(self.env.context.get('active_id'))
        base_domain = [
            ('picking_type_id', '=', picking_type.id),
            ('state', 'not in', ['cancel', 'done', 'draft'])
        ]

        picking_nums = 0
        additional_context = {'active_id': active_id}
        if barcode_type == 'product' or not barcode_type:
            product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
            if product:
                picking_nums = self.search_count(base_domain + [('product_id', '=', product.id)])
                additional_context['search_default_product_id'] = product.id
        if self.env.user.has_group('stock.group_tracking_lot') and (barcode_type == 'package' or (not barcode_type and not picking_nums)):
            package = self.env['stock.quant.package'].search([('name', '=', barcode)], limit=1)
            if package:
                pack_domain = ['|', ('move_line_ids.package_id', '=', package.id), ('move_line_ids.result_package_id', '=', package.id)]
                picking_nums = self.search_count(base_domain + pack_domain)
                additional_context['search_default_move_line_ids'] = barcode
        if self.env.user.has_group('stock.group_production_lot') and (barcode_type == 'lot' or (not barcode_type and not picking_nums)):
            lot = self.env['stock.lot'].search([
                ('name', '=', barcode),
                '|', ('company_id', '=', False), ('company_id', '=', picking_type.company_id.id),
            ], limit=1)
            if lot:
                lot_domain = [('move_line_ids.lot_id', '=', lot.id)]
                picking_nums = self.search_count(base_domain + lot_domain)
                additional_context['search_default_lot_id'] = lot.id
        if not barcode_type and not picking_nums:  # Nothing found yet, try to find picking by name.
            picking_nums = self.search_count(base_domain + [('name', '=', barcode)])
            additional_context['search_default_name'] = barcode

        if not picking_nums:
            if barcode_type:
                return {
                    'warning': {
                        'message': _("No %(picking_type)s ready for this %(barcode_type)s", picking_type=picking_type.name, barcode_type=barcode_type),
                    }
                }
            return {
                'warning': {
                    'title': _('No product, lot or package found for barcode %s', barcode),
                    'message': _('Scan a product, a lot/serial number or a package to filter the transfers.'),
                }
            }

        action = picking_type._get_action('stock_barcode.stock_picking_action_kanban')
        action['context'].update(additional_context)
        return {'action': action}
