from odoo import models, fields, api
import json
import logging

_logger = logging.getLogger(__name__)


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"
    menupro_id = fields.Char(string='Menu Pro ID')


    line_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('sent', 'Sent to Kitchen'),
        ],
        string="Order Line Status",
        default="draft",
        compute="_compute_line_status",
        store=True,
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'qty','line_status', 'attribute_value_ids', 'custom_attribute_value_ids', 'price_unit', 'skip_change', 'uuid',
            'price_subtotal', 'price_subtotal_incl', 'order_id', 'note', 'price_type', 'write_date',
            'product_id', 'discount', 'tax_ids', 'pack_lot_ids', 'customer_note', 'refunded_qty', 'price_extra',
            'full_product_name', 'refunded_orderline_id', 'combo_parent_id', 'combo_line_ids', 'combo_item_id',
            'refund_orderline_ids'
        ]

    @api.depends('order_id.last_order_preparation_change')
    def _compute_line_status(self):
        kitchen_lines = {}
        for line in self:
            # Loading kitchen_lines once
            if kitchen_lines == {}:
                last_change = line.order_id.last_order_preparation_change
                if not last_change:
                    continue
                kitchen_lines = self._load_kitchen_lines(last_change)

            # Tracks lines sent
            try:
                if line.uuid and line.uuid in kitchen_lines:
                    line.line_status = 'sent'
            except Exception as e:
                _logger.error("Error computing line status for line %s", line.id)
                _logger.error(e)
                line.line_status = 'draft'

    @api.model
    def _load_kitchen_lines(self, last_change):
        try:
            changes = json.loads(last_change)
            return changes.get('lines', {})
        except Exception as e:
            _logger.error("Failed to parse last_order_preparation_change JSON: %s", e)
            return {}
