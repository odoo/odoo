from odoo import models


class IrLogging(models.Model):
    _inherit = 'ir.logging'

    def _l10n_in_log_message(self, func: str, name: str, path: str, request: dict, response: dict, error_found: bool = False):
        # if error is found, then log request and response as message.
        if error_found:
            message = f"Request:\n{request}\n\nResponse:\n{response}"
        else:
            message = response
        self.env['ir.logging'].create({
            'func': func,
            'message': message,
            'name': name,
            'path': path,
            'level': 'INFO',
            'type': 'server',
            'line': ' ',
        })
