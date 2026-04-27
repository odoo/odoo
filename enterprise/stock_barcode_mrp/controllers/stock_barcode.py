# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.modules.module import get_resource_path
from odoo.tools.misc import file_open
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController


class MRPStockBarcode(StockBarcodeController):

    @http.route()
    def main_menu(self, barcode):
        action = self._try_open_production(barcode)
        if not action:
            action = self._try_create_production(barcode)
        return action or super().main_menu(barcode)

    @http.route('/stock_barcode_mrp/save_barcode_data', type='json', auth='user')
    def save_barcode_mrp_data(self, model_vals):
        """ Saves data from the barcode app, allows multiple model saves in the same http call

        :param model_vals: list of list with model name,res_id and a dict of write_vals
        :returns the barcode data from the mrp model passed
        """
        target_record = request.env['mrp.production']
        for model, res_id, vals in model_vals:
            if res_id == 0:
                record = request.env[model].with_context(newByProduct=vals.pop('byProduct', False)).create(vals)
                # difficult to use precompute as there are lots of depends fields to precompute
                if model == 'mrp.production':
                    record._compute_move_finished_ids()
            else:
                record = request.env[model].browse(res_id)
                for key in vals:
                    # check if dict val is passed for creation (for many2one, lot_producing_id in case of mrp)
                    if isinstance(vals[key], dict):
                        sub_model = request.env[model]._fields[key].comodel_name
                        vals[key] = request.env[sub_model].create(vals[key]).id
                record.write(vals)
        target_record = record if model == 'mrp.production' else record.production_id
        if target_record.state == 'draft':
            target_record.action_confirm()
        return target_record._get_stock_barcode_data()

    def _get_groups_data(self):
        group_data = super()._get_groups_data()
        group_data.update({
            'group_mrp_byproducts': request.env.user.has_group('mrp.group_mrp_byproducts')
        })
        return group_data

    def _try_create_production(self, barcode):
        """ If barcode represents a manufacure picking type, create and open a
        new manufacturing order.
        """
        picking_type = request.env['stock.picking.type'].search([
            ('barcode', '=', barcode),
            ('code', '=', 'mrp_operation'),
            ('company_id', 'in', [False, *self._get_allowed_company_ids()])
        ], limit=1)
        if picking_type:
            return request.env['mrp.production'].with_context({
                'default_company_id': picking_type.company_id.id,
                'default_picking_type_id': picking_type.id,
            })._get_new_production_client_action()
        return False

    def _try_open_production(self, barcode):
        """ If barcode represents a production order, open it
        """
        production = request.env['mrp.production'].search([
            ('name', '=', barcode),
        ], limit=1)
        if production:
            action = production.action_open_barcode_client_action()
            return {'action': action}
        return False

    @http.route()
    def print_inventory_commands(self, barcode_type=False):
        if barcode_type == "barcode_mrp_commands_and_operation_types" and not request.env.user.has_group('mrp.group_mrp_user'):
            return request.not_found()
        return super().print_inventory_commands(barcode_type=barcode_type)

    def _get_picking_type_domain(self, barcode_type, allowed_company_ids):
        if barcode_type == 'barcode_mrp_commands_and_operation_types':
            return [
                ('active', '=', 'True'),
                ('code', '=', 'mrp_operation'),
                ('barcode', '!=', ''),
                ('company_id', 'in', allowed_company_ids)]
        return super()._get_picking_type_domain(barcode_type, allowed_company_ids)

    def _get_barcode_pdfs(self, barcode_type, domain):
        barcode_pdfs = super()._get_barcode_pdfs(barcode_type, domain)
        if barcode_type != 'barcode_mrp_commands_and_operation_types':
            return barcode_pdfs
        file_path = get_resource_path('stock_barcode_mrp', 'static/img', 'barcodes_mrp_actions.pdf')
        with file_open(file_path, "rb") as commands_file:
            barcode_pdfs.insert(0, commands_file.read())
        return barcode_pdfs
