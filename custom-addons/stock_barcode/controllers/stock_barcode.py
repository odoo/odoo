# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import pdf, split_every
from odoo.tools.misc import file_open


class StockBarcodeController(http.Controller):

    @http.route('/stock_barcode/scan_from_main_menu', type='json', auth='user')
    def main_menu(self, barcode):
        """ Receive a barcode scanned from the main menu and return the appropriate
            action (open an existing / new picking) or warning.
        """
        barcode_type = None
        nomenclature = request.env.company.nomenclature_id
        if nomenclature.is_gs1_nomenclature:
            parsed_results = nomenclature.parse_barcode(barcode)
            if parsed_results:
                # search with the last feasible rule
                for result in parsed_results[::-1]:
                    if result['rule'].type in ['product', 'package', 'location', 'dest_location']:
                        barcode_type = result['rule'].type
                        break

        if not barcode_type:
            ret_open_picking = self._try_open_picking(barcode)
            if ret_open_picking:
                return ret_open_picking

            ret_open_picking_type = self._try_open_picking_type(barcode)
            if ret_open_picking_type:
                return ret_open_picking_type

        if request.env.user.has_group('stock.group_stock_multi_locations') and \
           (not barcode_type or barcode_type in ['location', 'dest_location']):
            ret_new_internal_picking = self._try_new_internal_picking(barcode)
            if ret_new_internal_picking:
                return ret_new_internal_picking

        if not barcode_type or barcode_type == 'product':
            ret_open_product_location = self._try_open_product_location(barcode)
            if ret_open_product_location:
                return ret_open_product_location

        if not barcode_type or barcode_type == 'lot':
            ret_open_lot_location = self._try_open_lot_location(barcode)
            if ret_open_lot_location:
                return ret_open_lot_location

        if request.env.user.has_group('stock.group_tracking_lot') and \
           (not barcode_type or barcode_type == 'package'):
            ret_open_package = self._try_open_package(barcode)
            if ret_open_package:
                return ret_open_package

        if request.env.user.has_group('stock.group_stock_multi_locations'):
            return {'warning': _('No picking or location or product corresponding to barcode %(barcode)s', barcode=barcode)}
        else:
            return {'warning': _('No picking or product corresponding to barcode %(barcode)s', barcode=barcode)}

    @http.route('/stock_barcode/save_barcode_data', type='json', auth='user')
    def save_barcode_data(self, model, res_id, write_field, write_vals):
        if not res_id:
            return request.env[model].barcode_write(write_vals)
        target_record = request.env[model].browse(res_id)
        target_record.write({write_field: write_vals})
        return target_record._get_stock_barcode_data()

    @http.route('/stock_barcode/get_barcode_data', type='json', auth='user')
    def get_barcode_data(self, model, res_id):
        """ Returns a dict with values used by the barcode client:
        {
            "data": <data used by the stock barcode> {'records' : {'model': [{<record>}, ... ]}, 'other_infos':...}, _get_barcode_data_prefetch
            "groups": <security group>, self._get_groups_data
        }
        """
        if not res_id:
            target_record = request.env[model].with_context(allowed_company_ids=self._get_allowed_company_ids())
        else:
            target_record = request.env[model].browse(res_id).with_context(allowed_company_ids=self._get_allowed_company_ids())
        data = target_record._get_stock_barcode_data()
        data['records'].update(self._get_barcode_nomenclature())
        data['precision'] = request.env['decimal.precision'].precision_get('Product Unit of Measure')
        mute_sound = request.env['ir.config_parameter'].sudo().get_param('stock_barcode.mute_sound_notifications')
        config = {'play_sound': bool(not mute_sound or mute_sound == "False")}
        return {
            'data': data,
            'groups': self._get_groups_data(),
            'config': config,
        }

    @http.route('/stock_barcode/get_specific_barcode_data', type='json', auth='user')
    def get_specific_barcode_data(self, barcode, model_name, domains_by_model=False):
        nomenclature = request.env.company.nomenclature_id
        # Adapts the search parameters for GS1 specifications.
        operator = '='
        limit = None if nomenclature.is_gs1_nomenclature else 1
        if nomenclature.is_gs1_nomenclature:
            try:
                # If barcode is digits only, cut off the padding to keep the original barcode only.
                barcode = str(int(barcode))
                operator = 'ilike'
            except ValueError:
                pass  # Barcode isn't digits only.

        domains_by_model = domains_by_model or {}
        barcode_field_by_model = self._get_barcode_field_by_model()
        result = defaultdict(list)
        model_names = model_name and [model_name] or list(barcode_field_by_model.keys())

        for model in model_names:
            domain = [
                (barcode_field_by_model[model], operator, barcode),
                ('company_id', 'in', [False, *self._get_allowed_company_ids()])
            ]
            domain_for_this_model = domains_by_model.get(model)
            if domain_for_this_model:
                domain = expression.AND([domain, domain_for_this_model])
            record = request.env[model].with_context(display_default_code=False).search(domain, limit=limit)
            if record:
                result[model] += record.read(request.env[model]._get_fields_stock_barcode(), load=False)
                if hasattr(record, '_get_stock_barcode_specific_data'):
                    additional_result = record._get_stock_barcode_specific_data()
                    for key in additional_result:
                        result[key] += additional_result[key]
        return result

    @http.route('/stock_barcode/rid_of_message_demo_barcodes', type='json', auth='user')
    def rid_of_message_demo_barcodes(self, **kw):
        """ Edit the main_menu client action so that it doesn't display the 'print demo barcodes sheet' message """
        if not request.env.user.has_group('stock.group_stock_user'):
            return request.not_found()
        action = request.env.ref('stock_barcode.stock_barcode_action_main_menu')
        action and action.sudo().write({'params': {'message_demo_barcodes': False}})

    @http.route('/stock_barcode/print_inventory_commands', type='http', auth='user')
    def print_inventory_commands(self, barcode_type=False):
        if not request.env.user.has_group('stock.group_stock_user'):
            return request.not_found()

        # make sure we use the selected company if possible
        allowed_company_ids = self._get_allowed_company_ids()

        # same domain conditions for picking types and locations
        domain = self._get_picking_type_domain(barcode_type, allowed_company_ids)

        # get fixed command barcodes
        barcode_pdfs = self._get_barcode_pdfs(barcode_type, domain)

        if not barcode_pdfs:
            raise UserError(_("Barcodes are not available."))
        merged_pdf = pdf.merge_pdf(barcode_pdfs)

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(merged_pdf))
        ]

        return request.make_response(merged_pdf, headers=pdfhttpheaders)

    def _try_open_lot_location(self, barcode):
        """ If barcode represent a lot, open a list/kanban view to show all
        the locations of this lot.
        """
        result = request.env['stock.lot'].search_read([
            ('name', '=', barcode),
        ], ['id', 'display_name'], limit=1)
        if result:
            tree_view_id = request.env.ref('stock.view_stock_quant_tree').id
            kanban_view_id = request.env.ref('stock_barcode.stock_quant_barcode_kanban_2').id
            return {
                'action': {
                    'name': result[0]['display_name'],
                    'res_model': 'stock.quant',
                    'views': [(tree_view_id, 'list'), (kanban_view_id, 'kanban')],
                    'type': 'ir.actions.act_window',
                    'domain': [('lot_id', '=', result[0]['id'])],
                    'context': {
                        'search_default_internal_loc': True,
                    },
                },
            }

    def _try_open_product_location(self, barcode):
        """ If barcode represent a product, open a list/kanban view to show all
        the locations of this product.
        """
        result = request.env['product.product'].search_read([
            ('barcode', '=', barcode),
        ], ['id', 'display_name'], limit=1)
        if result:
            tree_view_id = request.env.ref('stock.view_stock_quant_tree').id
            kanban_view_id = request.env.ref('stock_barcode.stock_quant_barcode_kanban_2').id
            return {
                'action': {
                    'name': result[0]['display_name'],
                    'res_model': 'stock.quant',
                    'views': [(tree_view_id, 'list'), (kanban_view_id, 'kanban')],
                    'type': 'ir.actions.act_window',
                    'domain': [('product_id', '=', result[0]['id'])],
                    'context': {
                        'search_default_internal_loc': True,
                    },
                }
            }

    def _try_open_picking_type(self, barcode):
        """ If barcode represent a picking type, open a new
        picking with this type
        """
        picking_type = request.env['stock.picking.type'].search([
            ('barcode', '=', barcode),
        ], limit=1)
        if picking_type:
            picking = request.env['stock.picking']._create_new_picking(picking_type)
            return picking._get_client_action()
        return False

    def _try_open_picking(self, barcode):
        """ If barcode represents a picking, open it
        """
        corresponding_picking = request.env['stock.picking'].search([
            ('name', '=', barcode),
        ], limit=1)
        if corresponding_picking:
            action = corresponding_picking.action_open_picking_client_action()
            return {'action': action}
        return False

    def _try_open_package(self, barcode):
        """ If barcode represents a package, open it.
        """
        package = request.env['stock.quant.package'].search([('name', '=', barcode)], limit=1)
        if package:
            view_id = request.env.ref('stock.view_quant_package_form').id
            return {
                'action': {
                    'name': 'Open package',
                    'res_model': 'stock.quant.package',
                    'views': [(view_id, 'form')],
                    'type': 'ir.actions.act_window',
                    'res_id': package.id,
                    'context': {'active_id': package.id}
                }
            }
        return False

    def _try_new_internal_picking(self, barcode):
        """ If barcode represents a location, open a new picking from this location
        """
        corresponding_location = request.env['stock.location'].search([
            ('barcode', '=', barcode),
            ('usage', '=', 'internal')
        ], limit=1)
        if corresponding_location:
            internal_picking_type = request.env['stock.picking.type'].search([('code', '=', 'internal')])
            warehouse = corresponding_location.warehouse_id
            if warehouse:
                internal_picking_type = internal_picking_type.filtered(lambda r: r.warehouse_id == warehouse)
            dest_loc = corresponding_location
            while dest_loc.location_id and dest_loc.location_id.usage == 'internal':
                dest_loc = dest_loc.location_id
            if internal_picking_type:
                # Create and confirm an internal picking
                picking = request.env['stock.picking'].create({
                    'picking_type_id': internal_picking_type[0].id,
                    'user_id': False,
                    'location_id': corresponding_location.id,
                    'location_dest_id': dest_loc.id,
                })
                picking.action_confirm()

                return picking._get_client_action()
            else:
                return {'warning': _('No internal operation type. Please configure one in warehouse settings.')}
        return False

    def _get_allowed_company_ids(self):
        """ Return the allowed_company_ids based on cookies.

        Currently request.env.company returns the current user's company when called within a controller
        rather than the selected company in the company switcher and request.env.companies lists the
        current user's allowed companies rather than the selected companies.

        :returns: List of active companies. The first company id in the returned list is the selected company.
        """
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        return [int(cid) for cid in cids.split(',')]

    def _get_picking_type_domain(self, barcode_type, allowed_company_ids):
        return [
            ('active', '=', 'True'),
            ('barcode', '!=', ''),
            ('company_id', 'in', allowed_company_ids)
        ]

    def _get_barcode_pdfs(self, barcode_type, domain):
        barcode_pdfs = []
        if barcode_type == 'barcode_commands_and_operation_types':
            with file_open('stock_barcode/static/img/barcodes_actions.pdf', "rb") as commands_file:
                barcode_pdfs.append(commands_file.read())

        if 'operation_types' in barcode_type:
            # get picking types barcodes
            picking_type_ids = request.env['stock.picking.type'].search(domain)
            for picking_type_batch in split_every(112, picking_type_ids.ids):
                picking_types_pdf, _content_type = request.env['ir.actions.report']._render_qweb_pdf('stock.action_report_picking_type_label', picking_type_batch)
                if picking_types_pdf:
                    barcode_pdfs.append(picking_types_pdf)

        # get locations barcodes
        if barcode_type == 'locations' and request.env.user.has_group('stock.group_stock_multi_locations'):
            locations_ids = request.env['stock.location'].search(domain)
            for location_ids_batch in split_every(112, locations_ids.ids):
                locations_pdf, _content_type = request.env['ir.actions.report']._render_qweb_pdf('stock.action_report_location_barcode', location_ids_batch)
                if locations_pdf:
                    barcode_pdfs.append(locations_pdf)
        return barcode_pdfs

    def _get_groups_data(self):
        return {
            'group_stock_multi_locations': request.env.user.has_group('stock.group_stock_multi_locations'),
            'group_tracking_owner': request.env.user.has_group('stock.group_tracking_owner'),
            'group_tracking_lot': request.env.user.has_group('stock.group_tracking_lot'),
            'group_production_lot': request.env.user.has_group('stock.group_production_lot'),
            'group_uom': request.env.user.has_group('uom.group_uom'),
            'group_stock_packaging': request.env.user.has_group('product.group_stock_packaging'),
        }

    def _get_barcode_nomenclature(self):
        company = request.env['res.company'].browse(self._get_allowed_company_ids()[0])
        nomenclature = company.nomenclature_id
        return {
            "barcode.nomenclature": nomenclature.read(load=False),
            "barcode.rule": nomenclature.rule_ids.read(load=False)
        }

    def _get_barcode_field_by_model(self):
        list_model = [
            'stock.location',
            'product.product',
            'product.packaging',
            'stock.picking',
            'stock.lot',
            'stock.quant.package',
        ]
        return {model: request.env[model]._barcode_field for model in list_model if hasattr(request.env[model], '_barcode_field')}
