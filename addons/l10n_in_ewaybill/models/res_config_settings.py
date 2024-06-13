# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import html_escape
from odoo.addons.l10n_in_ewaybill.tools.ewaybill_api import EWayBillApi


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_in_ewaybill_username = fields.Char(
        "Indian Ewaybill username",
        related='company_id.l10n_in_ewaybill_username',
        readonly=False
    )
    l10n_in_ewaybill_password = fields.Char(
        "Indian Ewaybill password",
        related='company_id.l10n_in_ewaybill_password',
        readonly=False
    )

    def l10n_in_ewaybill_test(self):
        self._l10n_in_check_gst_number()
        ewaybill_api = EWayBillApi(self.company_id)
        response = ewaybill_api._ewaybill_authenticate()
        response = {}
        if response.get('error') or not self.company_id._l10n_in_ewaybill_token_is_valid():
            error_message = _("Incorrect username or password, or the GST number on company does not match.")
            if response.get('error'):
                error_message = "\n".join([html_escape('[%s] %s' % (e.get('code'), e.get('message'))) for e in response['error']])
            raise UserError(error_message)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'sticky': False,
                'message': _("API credentials validated successfully"),
            }
        }
