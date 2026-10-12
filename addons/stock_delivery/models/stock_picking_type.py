# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    def _get_default_weight_uom(self):
        return self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    auto_print_carrier_labels = fields.Boolean(
        "Auto Print Carrier Labels",
        help="Automatically print the carrier labels of the picking when they are created.",
    )
    auto_print_export_documents = fields.Boolean(
        "Auto Print Export Documents",
        help=(
            "Automatically print the export documents of the picking when they are created. "
            "Availability of export documents depends on the carrier and the destination."
        ),
    )
    batch_group_by_carrier = fields.Boolean('Carrier', help="Automatically group batches by carriers")
    batch_max_weight = fields.Integer("Maximum weight",
                                      help="A transfer will not be automatically added to batches that will exceed this weight if the transfer is added to it.\n"
                                           "Leave this value as '0' if no weight limit.")
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name', readonly=True, default=_get_default_weight_uom)

    def _compute_weight_uom_name(self):
        for picking_type in self:
            picking_type.weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    @api.model
    def _get_batch_group_by_keys(self):
        return super()._get_batch_group_by_keys() + ['batch_group_by_carrier']
