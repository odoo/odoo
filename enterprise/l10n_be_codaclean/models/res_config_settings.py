from odoo import _, fields, models

from odoo.exceptions import UserError

from odoo.addons.l10n_be_codaclean.tools.iap_api import get_error_message


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_be_codaclean_iap_token = fields.Char(related="company_id.l10n_be_codaclean_iap_token", readonly=False)
    l10n_be_codaclean_is_connected = fields.Boolean(related="company_id.l10n_be_codaclean_is_connected")

    def l10n_be_codaclean_refresh_connection_status(self):
        self.ensure_one()
        result = self.company_id._l10n_be_codaclean_check_status()
        self.env.cr.commit()  # Persist the changes
        if not result['success']:
            raise UserError(get_error_message(result.get('error', {})))

        if self.company_id.l10n_be_codaclean_is_connected:
            args = ['success', _('Success'), _('Codaclean connection established.')]
        else:
            error = result.get('error', {})
            args = ['danger', _('Error'), get_error_message(error) if error else _('Codaclean connection failed.')]
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                **dict(zip(['type', 'title', 'message'], args)),
                'next': {
                    'type': 'ir.actions.act_window_close',
                },
            },
        }

    def l10n_be_codaclean_open_connection_wizard(self):
        self.ensure_one()
        result = self.company_id._l10n_be_codaclean_check_status()
        error = result.get('error', {})
        wizard = self.env['l10n_be_codaclean.connection.wizard'].create({
            'company_id': self.company_id.id,
            'username': result.get('username'),
            'warning': get_error_message(error) if error else False,
        })
        return wizard._action_open()
