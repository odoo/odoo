# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from operator import itemgetter

from odoo import api, fields, models, _


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    picking_type_code = fields.Selection(related='picking_type_id.code')

    def action_client_action(self):
        """ Open the mobile view specialized in handling barcodes on mobile devices.

        :return: the action used to select pickings for the new batch picking
        :rtype: dict
        """
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('stock_barcode_picking_batch.stock_barcode_picking_batch_client_action')
        return dict(action, context={'active_id': self.id})

    def action_open_batch_picking(self):
        """ Method to open the form view of the current record from a button on the kanban view.
        """
        self.ensure_one()
        view_id = self.env.ref('stock_picking_batch.stock_picking_batch_form').id
        return {
            'name': _('Open picking batch form'),
            'res_model': 'stock.picking.batch',
            'view_mode': 'form',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
        }

    def action_add_pickings_and_confirm(self, vals):
        self.ensure_one()
        self.write(vals)
        self.action_confirm()
        return self._get_stock_barcode_data()

    @api.model
    def open_new_batch_picking(self):
        """ Creates a new batch picking and opens client action to select its pickings.

        :return: see `action_client_action`
        """
        new_picking_batch = self.env['stock.picking.batch'].create({})
        return new_picking_batch.action_client_action()

    def action_cancel_from_barcode(self):
        self.ensure_one()
        view = self.env.ref('stock_barcode.stock_barcode_cancel_operation_view')
        return {
            'name': _('Cancel this batch transfer?'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock_barcode.cancel.operation',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': dict(self.env.context, default_batch_id=self.id),
        }

    @api.model
    def action_get_new_batch_status(self, picking_batch_id):
        """ Return the initial state of a new batch picking as a dict. """
        picking_batch = self.env['stock.picking.batch'].browse(picking_batch_id)
        picking_states = dict(self.env['stock.picking'].fields_get(['state'])['state']['selection'])
        allowed_picking_ids = picking_batch.allowed_picking_ids.filtered(lambda p: p.state == 'assigned')
        allowed_picking_types = sorted(allowed_picking_ids.mapped('picking_type_id').read(['name']), key=itemgetter('name'))
        allowed_picking_ids = sorted(allowed_picking_ids.read(['name', 'user_id', 'state', 'picking_type_id']), key=itemgetter('name'))
        # convert to selection label
        for picking in allowed_picking_ids:
            picking["state"] = picking_states[picking["state"]]

        return {
            'picking_batch_name': picking_batch.name,
            'allowed_picking_ids': allowed_picking_ids,
            'allowed_picking_types': allowed_picking_types,
        }

    @api.model
    def action_confirm_batch_picking(self, picking_batch_id, picking_ids=None):
        """ Confirms selected pickings for a batch picking.

        Errors are expected to be handled in parent class and automatically stops batch confirmation
        and pickings.write(...). If picking_ids=None or picking_ids.types not the same => expect UserError.

        :params picking_batch_id: newly created batch
        :params picking_ids: pickings ids to add to new batch
        :return: boolean if successful
        """
        if picking_ids:
            pickings = self.env['stock.picking'].browse(picking_ids)
            pickings.write({'batch_id': picking_batch_id})
        picking_batch = self.env['stock.picking.batch'].browse(picking_batch_id)
        return picking_batch.action_confirm()

    def _get_stock_barcode_data(self):
        picking_data = {}
        if not self.picking_ids:  # Add some data for new batch.
            allowed_picking_ids = self.allowed_picking_ids.filtered(lambda p: p.state == 'assigned')
            users = allowed_picking_ids.user_id
            batches = self | allowed_picking_ids.batch_id
            partners = allowed_picking_ids.partner_id
            picking_data['allowed_pickings'] = allowed_picking_ids.read(['name', 'picking_type_id', 'state', 'user_id', 'batch_id', 'partner_id'], False)
            picking_data['nomenclature_id'] = [self.env.company.nomenclature_id.id]
            picking_data['source_location_ids'] = []
            picking_data['destination_locations_ids'] = []
            picking_types = self.picking_type_id or allowed_picking_ids.picking_type_id
            picking_data['records'] = {
                'res.partner': partners.read(['name'], False),
                'res.users': users.read(['name'], False),
                'stock.picking.batch': batches.read(self._get_fields_stock_barcode(), False),
                'stock.picking.type': picking_types.read(['name'], False),
            }
        else:  # Get data from batch's pickings.
            picking_data = self.picking_ids._get_stock_barcode_data()
            picking_data['records']['stock.picking.batch'] = self.read(self._get_fields_stock_barcode(), load=False)
        # Add picking_id sorted by name to be consistent with the older version.
        for batch in picking_data['records']['stock.picking.batch']:
            batch['picking_ids'] = self.browse(batch['id']).picking_ids.sorted(key=lambda p: (p.name, p.id)).ids

        picking_data['line_view_id'] = self.env.ref('stock_barcode_picking_batch.stock_move_line_product_selector_inherit').id
        picking_data['form_view_id'] = self.env.ref('stock_barcode_picking_batch.stock_barcode_batch_picking_view_info').id
        return picking_data

    @api.model
    def _get_fields_stock_barcode(self):
        return [
            'company_id',
            'move_ids',
            'move_line_ids',
            'name',
            'picking_type_id',
            'picking_type_code',
            'state',
            'user_id',
        ]

    @api.model
    def filter_on_barcode(self, barcode):
        action = self.env['stock.picking'].filter_on_barcode(barcode)
        return action
