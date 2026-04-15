# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import _, fields, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    printer_ids = fields.Many2many(
        'printer.printer',
        'report_printer_rel',
        'report_id',
        'printer_id',
        string="Printer",
        help="Select the printers for this report.",
    )

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

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {'printer_ids'}

    def report_action(self, docids, data=None, config=True):
        result = super().report_action(docids, data, config)
        if result.get('type') != 'ir.actions.report':
            return result

        result['id'] = self.id
        result['printer_ids'] = self.printer_ids.ids
        return result

    def get_printer_selection_wizard(self, printer_ids):
        self.ensure_one()
        if printer_ids:
            printer_ids = [p for p in printer_ids if p in self.printer_ids.ids]

        wizard = self.env['select.printer.wizard'].create({
            'display_printer_ids': self.printer_ids.ids,
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
