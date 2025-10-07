from odoo import models


class IrLogging(models.Model):
    _inherit = 'ir.logging'

    def _l10n_in_log_message(self, func: str, message: str, name: str, path: str):
        self.env['ir.logging'].create({
            'func': func,
            'message': message,
            'name': name,
            'path': path,
            'level': 'INFO',
            'type': 'server',
            'line': ' ',
        })
