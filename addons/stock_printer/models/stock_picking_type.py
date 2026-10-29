# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    auto_print_carrier_labels = fields.Boolean(
        "Auto Print Carrier Labels",
        help="If this checkbox is ticked, Odoo will automatically print the carrier labels of a picking when it is "
             "validated, on the printers of the Shipping Labels report.")
    auto_print_export_documents = fields.Boolean(
        "Auto Print Export Documents",
        help="If this checkbox is ticked, Odoo will automatically print the export documents of a picking when it is "
             "validated, on the printers of the Shipping Documents report.")

    def action_open_shipping_labels_report(self):
        self.ensure_one()
        return self._get_report_form_action('stock_printer.action_report_shipping_labels')

    def action_open_shipping_documents_report(self):
        self.ensure_one()
        return self._get_report_form_action('stock_printer.action_report_shipping_documents')

    def _get_report_form_action(self, report_xml_id):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.actions.report',
            'res_id': self.env.ref(report_xml_id).id,
            'views': [(False, 'form')],
            'context': {'printer_required': True},
        }
