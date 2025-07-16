# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.exceptions import UserError, RedirectWarning


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_in_edi_username = fields.Char("Indian EDI username", related="company_id.l10n_in_edi_username", readonly=False)
    l10n_in_edi_password = fields.Char("Indian EDI password", related="company_id.l10n_in_edi_password", readonly=False)

    def l10n_in_edi_test(self):
        self._l10n_in_check_gst_number()
        response = self.company_id._l10n_in_edi_authenticate()
        if response.get('error'):
            raise UserError("\n".join(["[%s] %s" % (e.get('code'), (e.get('message'))) for e in response['error']]))
        elif not self.company_id.sudo()._l10n_in_edi_token_is_valid():
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
