# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, http, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
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
        request.update_context(allowed_company_ids=self._get_allowed_company_ids())
        nomenclature = request.env.company.nomenclature_id
        try:
            parsed_results = nomenclature.parse_barcode(barcode)
        except ValidationError:
            parsed_results = False
        if parsed_results and nomenclature.is_gs1_nomenclature:
            # search with the last feasible rule
            for result in parsed_results[::-1]:
                if result['type'] in ['product', 'package', 'location', 'location_dest']:
                    barcode_type = result['type']
                    break

        # Alias support
        elif parsed_results:
            for res in parsed_results if isinstance(parsed_results, list) else [parsed_results]:
                if res['type'] in ['price', 'weight']:
                    barcode = res['base_code']
                    barcode_type = 'product'
                    break
                barcode = res.get('code', barcode)
                break

        if not barcode_type:
            ret_open_picking = self._try_open_picking(barcode)
            if ret_open_picking:
                return ret_open_picking

            ret_open_picking_type = self._try_open_picking_type(barcode)
            if ret_open_picking_type:
                return ret_open_picking_type

        if request.env.user.has_group('stock.group_stock_multi_locations') and \
           (not barcode_type or barcode_type in ['location', 'location_dest']):
            ret_new_internal_picking = self._try_new_internal_picking(barcode)
            if ret_new_internal_picking:
                return ret_new_internal_picking

        if not barcode_type or barcode_type == 'product':
            ret_open_product_location = self._try_open_product_location(barcode)
            if ret_open_product_location:
                return ret_open_product_location

        if request.env.user.has_group('stock.group_production_lot') and \
           (not barcode_type or barcode_type == 'lot'):
            ret_open_lot = self._try_open_lot(barcode)
            if ret_open_lot:
                return ret_open_lot

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
        data['config'] = data.get('config', {})
        data['config']['play_sound'] = bool(not mute_sound or mute_sound == "False")
        data['config']['barcode_separator_regex'] = request.env['ir.config_parameter'].sudo().get_param('stock_barcode.barcode_separator_regex', '.^')
        data['config']['barcode_rfid_batch_time'] = int(request.env['ir.config_parameter'].sudo().get_param('stock_barcode.barcode_rfid_batch_time', 1000))
        delay_between_scan = request.env['ir.config_parameter'].sudo().get_param('stock_barcode.delay_between_scan')
        if delay_between_scan and delay_between_scan.isnumeric():
            data['config']['delay_between_scan'] = int(delay_between_scan)
        return {
            'data': data,
            'groups': self._get_groups_data(),
        }

    @http.route('/stock_barcode/get_main_menu_data', type='json', auth='user')
    def get_main_menu_data(self):
        user = request.env.user
        groups = {
            'locations': user.has_group('stock.group_stock_multi_locations'),
            'package': user.has_group('stock.group_tracking_lot'),
            'tracking': user.has_group('stock.group_production_lot'),
        }
        quant_count = request.env['stock.quant'].search_count([
            ("user_id", "=?", user.id),
            ("location_id.usage", "in", ["internal", "transit"]),
            ("inventory_date", "<=", fields.Date.context_today(user)),
        ])
        mute_sound = request.env['ir.config_parameter'].sudo().get_param('stock_barcode.mute_sound_notifications')
        play_sound = bool(not mute_sound or mute_sound == "False")
        return {
            'groups': groups,
            'play_sound': play_sound,
            'quant_count': quant_count,
        }

    def _get_records_fields_stock_barcode(self, records):
        result = defaultdict(list)
        result[records._name] = records.read(records._get_fields_stock_barcode(), load=False)
        if hasattr(records, '_get_stock_barcode_specific_data'):
            records_data_by_model = records._get_stock_barcode_specific_data()
            for res_model in records_data_by_model:
                result[res_model] += records_data_by_model[res_model]
        return result

    @http.route('/stock_barcode/get_quants', type='json', auth='user')
    def get_existing_quant_and_related_data(self, domain):
        quants = request.env['stock.quant'].search(domain)
        return quants.get_stock_barcode_data_records()

    @http.route('/stock_barcode/get_specific_barcode_data', type='json', auth='user')
    def get_specific_barcode_data(self, **kwargs):
        """ This method gets multiple records data from different models for the given barcode(s).
        The goal is to do one search by model (plus the additional record, e.g. the UOM records when
        fetching product's records.)
        :param kwargs:
            ''barcode'': a single barcode (string), used when not knowing which model is linked.
            ''barcodes_by_model'': a dict of model_name -> barcode list
            ''context''
            ''domains_by_model'': a dict of model_name -> domain
            ''fetch_quant'': Fetch extra quants based on products (used in inventory)
        """
        request.env.context = {**kwargs.get('context', {}), **request.env.context, 'display_default_code': False}
        barcodes_by_model = kwargs.get('barcodes_by_model')
        domains_by_model = kwargs.get('domains_by_model', {})
        universal_domain = domains_by_model.get('all')
        fetch_quant = kwargs.get('fetch_quants')
        nomenclature = request.env.company.nomenclature_id
        result = defaultdict(list)
        product_ids = set()

        if barcodes_by_model and barcodes_by_model.get('product.product') and not barcodes_by_model.get('stock.lot'):
            barcodes_by_model['stock.lot'] = []

        # If a barcode was given but no model was specified, search for it for all relevant models.
        if not barcodes_by_model:
            barcode_field_by_model = self._get_barcode_field_by_model()
            barcodes = kwargs.get('barcodes') or [kwargs.get('barcode')]
            barcodes_by_model = {model_name: barcodes for model_name in barcode_field_by_model.keys()}

        for model_name, barcodes in barcodes_by_model.items():
            if not barcodes:
                continue
            barcode_field = request.env[model_name]._barcode_field
            domain = [(barcode_field, 'in', barcodes)]

            if nomenclature.is_gs1_nomenclature:
                # If we use GS1 nomenclature, the domain might need some adjustments.
                converted_barcodes_domain = []
                unconverted_barcodes = []
                for barcode in set(barcodes):
                    try:
                        # If barcode is digits only, cut off the padding to keep the original barcode only.
                        barcode = str(int(barcode))
                        if converted_barcodes_domain:
                            converted_barcodes_domain = expression.OR([
                                converted_barcodes_domain,
                                [(barcode_field, 'ilike', barcode)]
                            ])
                        else:
                            converted_barcodes_domain = [(barcode_field, 'ilike', barcode)]
                    except ValueError:
                        unconverted_barcodes.append(barcode)
                        pass  # Barcode isn't digits only.
                if converted_barcodes_domain:
                    domain = converted_barcodes_domain
                    if unconverted_barcodes:
                        domain = expression.OR([
                            domain,
                            [(barcode_field, 'in', unconverted_barcodes)]
                        ])
            # Adds additionnal domain if applicable.
            domain_for_this_model = domains_by_model.get(model_name)
            if domain_for_this_model:
                domain = expression.AND([domain, domain_for_this_model])
            if universal_domain:
                domain = expression.AND([domain, universal_domain])
            # Search for barcodes' records.
            records = request.env[model_name].search(domain)
            fetched_data = self._get_records_fields_stock_barcode(records)
            if fetch_quant and model_name == 'product.product':
                product_ids = records.ids
            for f_model_name in fetched_data:
                result[f_model_name] = result[f_model_name] + fetched_data[f_model_name]

        if fetch_quant and product_ids:
            quants = request.env['stock.quant'].search([
                ('product_id', 'in', product_ids),
                ('location_id.usage', '=', 'internal'),
            ])
            fetched_data = self._get_records_fields_stock_barcode(quants)

            for f_model_name in fetched_data:
                result[f_model_name] = result[f_model_name] + fetched_data[f_model_name]
        return result

    @http.route('/stock_barcode/get_specific_barcode_data_batch', type='json', auth='user')
    def get_specific_barcode_data_batch(self, kwargs):
        """ Batched version of `get_specific_barcode_data`, where its purpose is to get multiple
        records data from different models. The goal is to do one search by model (plus the
        additional record, e.g. the UOM records when fetching product's records.)
        """
        nomenclature = request.env.company.nomenclature_id
        result = defaultdict(list)

        for model_name, barcodes in kwargs.items():
            barcode_field = request.env[model_name]._barcode_field
            domain = [(barcode_field, 'in', barcodes)]

            if nomenclature.is_gs1_nomenclature:
                # If we use GS1 nomenclature, the domain might need some adjustments.
                converted_barcodes_domain = []
                unconverted_barcodes = []
                for barcode in barcodes:
                    try:
                        # If barcode is digits only, cut off the padding to keep the original barcode only.
                        barcode = str(int(barcode))
                        if converted_barcodes_domain:
                            converted_barcodes_domain = expression.OR([
                                converted_barcodes_domain,
                                [(barcode_field, 'ilike', barcode)]
                            ])
                        else:
                            converted_barcodes_domain = [(barcode_field, 'ilike', barcode)]
                    except ValueError:
                        unconverted_barcodes.append(barcode)
                        pass  # Barcode isn't digits only.
                if converted_barcodes_domain:
                    domain = converted_barcodes_domain
                    if unconverted_barcodes:
                        domain = expression.OR([
                            domain,
                            [(barcode_field, 'in', unconverted_barcodes)]
                        ])

            records = request.env[model_name].search(domain)
            fetched_data = self._get_records_fields_stock_barcode(records)
            for f_model_name in fetched_data:
                result[f_model_name] = result[f_model_name] + fetched_data[f_model_name]
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

    def _try_open_lot(self, barcode):
        """ If barcode represent a lot, open a form view to show all
        the details of this lot.
        """
        result = request.env['stock.lot'].search_read([
            ('name', '=', barcode),
        ], ['id', 'display_name'], limit=1)
        if result:
            return {
                'action': {
                    'name': 'Open lot',
                    'res_model': 'stock.lot',
                    'views': [(request.env.ref('stock.view_production_lot_form').id, 'form')],
                    'type': 'ir.actions.act_window',
                    'res_id': result[0]['id'],
                }
            }
        return False

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
                    'mobile_view_mode': 'kanban',
                }
            }

    def _try_open_picking_type(self, barcode):
        """ If barcode represent a picking type, open a new
        picking with this type
        """
        picking_type = request.env['stock.picking.type'].search([
            ('barcode', '=', barcode),
            ('company_id', 'in', [False, *self._get_allowed_company_ids()]),
        ], limit=1)
        if picking_type:
            picking = request.env['stock.picking']._create_new_picking(picking_type)
            action = picking.action_open_picking_client_action()
            return {'action': action}
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
            ('usage', '=', 'internal'),
            ("company_id", "=", self._get_allowed_company_ids()[0])
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
                action = picking.action_open_picking_client_action()
                return {'action': action}
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
        cids = request.cookies.get('cids', str(request.env.user.company_id.id))
        return [int(cid) for cid in cids.split('-')]

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
            'group_stock_sign_delivery': request.env.user.has_group('stock.group_stock_sign_delivery'),
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
            'stock.package.type',
        ]
        return {model: request.env[model]._barcode_field for model in list_model if hasattr(request.env[model], '_barcode_field')}
