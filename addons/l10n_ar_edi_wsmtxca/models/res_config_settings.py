# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import _, models
from odoo.exceptions import UserError
# Faltaría `fields` si se usa, pero no en este fragmento.


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def l10n_ar_connection_test(self):
        self.ensure_one()
        errors_list = []
        if not self.l10n_ar_afip_ws_crt:
            
            errors_list.append(_("* Please set a certificate in order to make the test"))
        if not self.l10n_ar_afip_ws_key:
            
            errors_list.append(_("* Please set a private key in order to make the test"))
        if errors_list:
            raise UserError("\n".join(errors_list))

        res_parts = []
        for webservice in ["wsfe", "wsfex", "wsbfe", "wscdc", "wsmtxca"]:
            try:
                self.company_id._l10n_ar_get_connection(webservice)
                
                res_parts.append(_("* %s: Connection is available") % webservice)
            except UserError as error_user:
                hint_msg_match = re.search(r".*(HINT|CONSEJO): (.*)", str(error_user.args[0])) # error.name no existe, es error.args[0]
                if hint_msg_match:
                    msg = (
                        hint_msg_match.groups()[-1]
                        if hint_msg_match and len(hint_msg_match.groups()) > 1
                        else "\n".join(
                            # Asegurarse que error.args[0] es string
                            re.search(
                                r".*" + webservice + r": (.*)\n\n", str(error_user.args[0])
                            ).groups() if re.search(r".*" + webservice + r": (.*)\n\n", str(error_user.args[0])) else [str(error_user.args[0])]
                        )
                    )
                else:
                    msg = str(error_user.args[0]) # error.name no existe
                
                res_parts.append(
                    _("* %(webservice)s: Connection failed. %(message)s") % {'webservice': webservice, 'message': msg.strip()}
                )
            except Exception as error_generic: # BLE001
                
                res_parts.append(
                    _("* %(webservice)s: Connection failed. This is what we get: %(error_repr)s")
                    % {'webservice': webservice, 'error_repr': repr(error_generic)}
                ) # noqa: BLE001
        raise UserError("\n".join(res_parts))