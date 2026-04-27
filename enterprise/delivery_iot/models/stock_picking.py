# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons.web.controllers.utils import clean_action


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    iot_scale_ids = fields.Many2many(
        'iot.device',
        string="Scales",
        domain=[('type', '=', 'scale')],
        help="Choose the scales you want to use for this operation type. Those scales can be used to weigh the packages created."
    )
    auto_print_carrier_labels = fields.Boolean(
        "Auto Print Carrier Labels",
        help="If this checkbox is ticked, Odoo will automatically print the carrier labels of the picking when they are created. Note this requires a printer to be assigned to this report.")
    auto_print_export_documents = fields.Boolean(
        "Auto Print Export Documents",
        help="If this checkbox is ticked, Odoo will automatically print the export documents of the picking when they are created. Availability of export documents depends on the carrier and the destination. Note this requires a printer to be assigned to this report. ")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _get_autoprint_report_actions(self):
        report_actions = []
        shipping_labels_to_print = self.filtered(lambda p: p.picking_type_id.auto_print_carrier_labels)
        if shipping_labels_to_print:
            action = self.env.ref("delivery_iot.action_report_shipping_labels").report_action(shipping_labels_to_print.ids, config=False)
            clean_action(action, self.env)
            report_actions.append(action)
        shipping_documents_to_print = self.filtered(lambda p: p.picking_type_id.auto_print_export_documents)
        if shipping_documents_to_print:
            action = self.env.ref("delivery_iot.action_report_shipping_docs").report_action(shipping_documents_to_print.ids, config=False)
            clean_action(action, self.env)
            report_actions.append(action)
        return report_actions + super()._get_autoprint_report_actions()

    def print_attachment(self, attachments):
        """Unused method, kept to avoid breaking the API."""
        pass
