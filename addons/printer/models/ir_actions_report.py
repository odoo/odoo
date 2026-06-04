# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import _, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def generate_print_data(self, printer_ids, res_ids, data=None):
        self.ensure_one()
        printers = self.env['printer.printer'].browse(printer_ids)
        content_bytes, _ = self._render(self.report_name, res_ids, data=data)
        return [{
            'payload': base64.b64encode(content_bytes).decode('utf-8'),
            'printer': {
                'id': printer.id,
                'name': printer.name,
                'printer_ip': printer.printer_ip,
                'printer_type': printer.printer_type,
            },
        } for printer in printers]

    def get_printer_selection_wizard(self, printer_ids):
        self.ensure_one()
        wizard = self.env['select.printer.wizard'].create({
            'printer_ids': printer_ids,
        })
        return {
            'name': _("Select Printers for %s", self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'select.printer.wizard',
            'res_id': wizard.id,
            'target': 'new',
            'views': [(False, 'form')],
            'context': {
                'report_id': self.id,
            },
        }
