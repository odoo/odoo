# -*- coding: utf-8 -*-

from odoo import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model_create_multi
    def create(self, vals_list):
        """Track stock picking creation."""
        pickings = super().create(vals_list)

        for picking in pickings:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='stock_picking_create',
                    description=f'Stock picking created: {picking.name} ({picking.picking_type_id.name})',
                    model_name='stock.picking',
                    res_id=picking.id,
                    resource_name=picking.name,
                    severity='info',
                    success=True,
                    new_values={
                        'name': picking.name,
                        'picking_type': picking.picking_type_id.name,
                        'partner': picking.partner_id.name if picking.partner_id else None,
                        'location_src': picking.location_id.complete_name,
                        'location_dest': picking.location_dest_id.complete_name,
                        'scheduled_date': str(picking.scheduled_date) if picking.scheduled_date else None,
                        'origin': picking.origin,
                    }
                )
            except Exception as e:
                # Don't fail the operation if logging fails
                pass

        return pickings

    def button_validate(self):
        """Track stock picking validation."""
        # Store info before validation
        picking_info = [(p.id, p.name, p.picking_type_id.name) for p in self]

        result = super().button_validate()

        for picking_id, picking_name, picking_type in picking_info:
            try:
                picking = self.browse(picking_id)
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='stock_picking_validate',
                    description=f'Stock picking validated: {picking_name} ({picking_type})',
                    model_name='stock.picking',
                    res_id=picking_id,
                    resource_name=picking_name,
                    severity='info',
                    success=True,
                    additional_data={
                        'picking_type': picking_type,
                        'move_lines_count': len(picking.move_ids),
                        'state': picking.state,
                    }
                )
            except:
                pass

        return result

    def action_cancel(self):
        """Track stock picking cancellation."""
        # Store info before cancellation
        picking_info = [(p.id, p.name, p.picking_type_id.name, p.state) for p in self]

        result = super().action_cancel()

        for picking_id, picking_name, picking_type, old_state in picking_info:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='stock_picking_cancel',
                    description=f'Stock picking cancelled: {picking_name} ({picking_type})',
                    model_name='stock.picking',
                    res_id=picking_id,
                    resource_name=picking_name,
                    severity='warning',
                    success=True,
                    old_values={'state': old_state},
                    new_values={'state': 'cancel'},
                    additional_data={'picking_type': picking_type}
                )
            except:
                pass

        return result

    def write(self, vals):
        """Track important field changes in stock pickings."""
        # Store old values for significant fields
        tracked_fields = ['state', 'location_id', 'location_dest_id', 'scheduled_date', 'date_done']
        old_values_list = []

        if any(field in vals for field in tracked_fields):
            for picking in self:
                old_vals = {}
                if 'state' in vals:
                    old_vals['state'] = picking.state
                if 'location_id' in vals:
                    old_vals['location_src'] = picking.location_id.complete_name
                if 'location_dest_id' in vals:
                    old_vals['location_dest'] = picking.location_dest_id.complete_name
                if 'scheduled_date' in vals:
                    old_vals['scheduled_date'] = str(picking.scheduled_date) if picking.scheduled_date else None
                if 'date_done' in vals:
                    old_vals['date_done'] = str(picking.date_done) if picking.date_done else None

                if old_vals:
                    old_values_list.append((picking.id, picking.name, old_vals))

        result = super().write(vals)

        # Log significant changes
        for picking_id, picking_name, old_vals in old_values_list:
            try:
                picking = self.browse(picking_id)
                new_vals = {}
                if 'state' in vals:
                    new_vals['state'] = picking.state
                if 'location_id' in vals:
                    new_vals['location_src'] = picking.location_id.complete_name
                if 'location_dest_id' in vals:
                    new_vals['location_dest'] = picking.location_dest_id.complete_name
                if 'scheduled_date' in vals:
                    new_vals['scheduled_date'] = str(picking.scheduled_date) if picking.scheduled_date else None
                if 'date_done' in vals:
                    new_vals['date_done'] = str(picking.date_done) if picking.date_done else None

                # Only log if state changed to done (not already logged by button_validate)
                if 'state' in vals and vals['state'] == 'done' and old_vals.get('state') != 'done':
                    # Skip if this was done via button_validate (already logged)
                    pass
                elif new_vals:
                    self.env['camtel.audit.log'].sudo().create_log(
                        event_type='stock_picking_create',  # Generic modify event
                        description=f'Stock picking modified: {picking_name}',
                        model_name='stock.picking',
                        res_id=picking_id,
                        resource_name=picking_name,
                        old_values=old_vals,
                        new_values=new_vals,
                        severity='info',
                        success=True,
                    )
            except:
                pass

        return result
