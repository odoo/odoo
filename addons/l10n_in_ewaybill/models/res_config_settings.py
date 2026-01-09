# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import html_escape
from odoo.addons.l10n_in_ewaybill.tools.ewaybill_api import EWayBillApi, EWayBillError


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
    l10n_in_ewaybill_feature = fields.Boolean(related='company_id.l10n_in_ewaybill_feature', readonly=False)

    def l10n_in_ewaybill_test(self):
        self._l10n_in_check_gst_number()
        ewaybill_api = EWayBillApi(self.company_id)
        try:
            ewaybill_api._ewaybill_authenticate()
        except EWayBillError as e:
            raise UserError(e.get_all_error_message())
        if not self.company_id.sudo()._l10n_in_ewaybill_token_is_valid():
            raise UserError(_("Incorrect username or password, or the GST number on company does not match."))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'sticky': False,
                'message': _("API credentials validated successfully"),
            }
        }

    def _l10n_in_gsp_provider_changed(self):
        """
            This change should effect all Indian companies so we search for them and
            Invalidate existing tokens if GSP provider changed
        """
        self.env['res.company'].sudo().search([('account_fiscal_country_id.code', '=', 'IN')]).write({
            'l10n_in_ewaybill_auth_validity': False,
        })
        super()._l10n_in_gsp_provider_changed()
