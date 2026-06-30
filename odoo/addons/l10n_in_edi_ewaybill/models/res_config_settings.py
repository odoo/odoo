# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import html_escape


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_in_edi_ewaybill_username = fields.Char("Indian EDI Stock username",
        related="company_id.l10n_in_edi_ewaybill_username", readonly=False)
    l10n_in_edi_ewaybill_password = fields.Char("Indian EDI Stock password",
        related="company_id.l10n_in_edi_ewaybill_password", readonly=False)

    def l10n_in_edi_ewaybill_test(self):
        self.l10n_in_check_gst_number()
        response = self.env["account.edi.format"]._l10n_in_edi_ewaybill_authenticate(self.company_id)
        if response.get("error") or not self.company_id.sudo()._l10n_in_edi_ewaybill_token_is_valid():
            error_message = _("Incorrect username or password, or the GST number on company does not match.")
            if response.get("error"):
                error_message = "\n".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in response["error"]])
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
