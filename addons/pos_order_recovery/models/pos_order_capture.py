
import logging
import json

from odoo import _, api, fields, models
from odoo.addons.point_of_sale.models.pos_session import POS_CAPTURE_PREFIX, POS_CAPTURE_SUFFIX, POS_CAPTURE_SEPARATOR
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrderCapture(models.Model):
    _name = 'pos.order.capture'
    _description = 'Point of Sale capture order'

    name = fields.Char(compute='_compute_name', store=True, readonly=True)
    json_content_id = fields.Many2one('ir.attachment', required=True, readonly=True, ondelete='cascade')
    order_name = fields.Char(required=True, readonly=True, index=True)
    order_hash = fields.Integer(required=True, readonly=True, index=True)
    session_id = fields.Many2one('pos.session', string='Session', required=True, readonly=True, index=True)

    json_content_text = fields.Text(compute='_compute_json_content')
    traceback_text = fields.Text(compute='_compute_json_content')
    conflicting_capture_count = fields.Integer(compute='_compute_conflicting_capture_count')

    @api.model
    def _generate_capture_record_from_existing_capture_attachments(self):
        # Get the existing data from the other model
        existing_captured_orders = self.env['ir.attachment'].search([
            ['name', '=like', f"{POS_CAPTURE_PREFIX}%{POS_CAPTURE_SUFFIX}"]
        ])

        # Create the new records based on the existing data
        for existing_captured_order in existing_captured_orders:
            order_name, order_hash = existing_captured_order.name[len(POS_CAPTURE_PREFIX): -len(POS_CAPTURE_SUFFIX)].split(POS_CAPTURE_SEPARATOR, 1)
            self.create({
                'json_content_id': existing_captured_order.id,
                'order_name': order_name,
                'order_hash': order_hash,
                'session_id': existing_captured_order.res_id,
            })

    def action_compare_conflicting_capture(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Compare Conflicting Capture",
            "res_model": "pos.order.capture.comparer.wizard",
            "view_mode": "form",
            "target": "new",
            "view_id": self.env.ref('pos_order_recovery.compare_conflicting_capture_wizard_view').id,
        }

    @api.depends('order_name', 'order_hash')
    def _compute_name(self):
        for capture in self:
            capture.name = f"Unsynced {capture.order_name} (#{capture.order_hash})"

    def _compute_json_content(self):
        for capture in self:
            capture.json_content_text = capture.with_context(bin_size=False).json_content_id.raw

            json_data = capture.get_json_dict_content()
            capture.traceback_text = ''.join(json_data.get('traceback', []))

    def get_json_dict_content(self):
        self.ensure_one()
        return json.loads(self.json_content_text)

    def _compute_conflicting_capture_count(self):
        for capture in self:
            capture.conflicting_capture_count = self.search_count(
                [('order_name', '=', capture.order_name)]
                ) - 1  # Don't count ourself

    def _sync(self):
        conflicting_orders = self.filtered_domain([["conflicting_capture_count", "!=", 0]])
        if conflicting_orders:
            raise UserError(_(
                "Operation cancelled.\n" \
                "At least one of the selected unsynced order have conflict for the same order reference: %s.\n" \
                "You can choose the file to keep using the smart button on the form view", 
                conflicting_orders
                )
            )
        
        pos_order_model = self.env['pos.order']
        for capture_order in self:
            _logger.info('Manual PoS order sync using %s', capture_order)
            pos_order_model.create_from_ui([capture_order.get_json_dict_content()], draft=False)
