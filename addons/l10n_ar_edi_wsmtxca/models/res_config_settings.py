# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import _, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def l10n_ar_connection_test(self):
        self.ensure_one()
        error = ""
        if not self.l10n_ar_afip_ws_crt:
            error += "\n* " + _("Please set a certificate in order to make the test")
        if not self.l10n_ar_afip_ws_key:
            error += "\n* " + _("Please set a private key in order to make the test")
        if error:
            raise UserError(error)

        res = ""
        for webservice in ["wsfe", "wsfex", "wsbfe", "wscdc", "wsmtxca"]:
            try:
                self.company_id._l10n_ar_get_connection(webservice)
                res += ("\n* %s: " + _("Connection is available")) % webservice
            except UserError as error:
                hint_msg = re.search(".*(HINT|CONSEJO): (.*)", error.name)
                if hint_msg:
                    msg = (
                        hint_msg.groups()[-1]
                        if hint_msg and len(hint_msg.groups()) > 1
                        else "\n".join(
                            re.search(
                                ".*" + webservice + ": (.*)\n\n", error.name
                            ).groups()
                        )
                    )
                else:
                    msg = error.name
                res += (
                    "\n* %s: " % webservice
                    + _("Connection failed")
                    + ". %s" % msg.strip()
                )
            except Exception as error:
                res += (
                    "\n* %s: "
                    + _("Connection failed")
                    + ". "
                    + _("This is what we get")
                    + " %s"
                ) % (webservice, repr(error))
        raise UserError(res)
