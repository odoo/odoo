# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.web.controllers.utils import clean_action


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_autoprint_report_actions(self):
        report_actions = super()._get_autoprint_report_actions()
        # The carriers save the labels and export documents in the chatter when
        # the transfer is validated; they only make sense printed on printers.
        for option, report_xml_id in (
            ('auto_print_carrier_labels', 'stock_printer.action_report_shipping_labels'),
            ('auto_print_export_documents', 'stock_printer.action_report_shipping_documents'),
        ):
            pickings = self.filtered(lambda p: p.picking_type_id[option])
            report = self.env.ref(report_xml_id)
            if pickings and report.sudo().printer_ids:
                action = report.report_action(pickings.ids, config=False)
                report_actions.append(clean_action(action, self.env))
        return report_actions
