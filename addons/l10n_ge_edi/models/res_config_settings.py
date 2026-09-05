from odoo import fields, models

from odoo.addons.l10n_ge_edi.tools.rsge_client import RSgeError, translate_rsge_error


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ge_edi_su = fields.Char(related="company_id.l10n_ge_edi_su", readonly=False)
    l10n_ge_edi_sp = fields.Char(related="company_id.l10n_ge_edi_sp", readonly=False)

    def action_l10n_ge_edi_test_connection(self):
        self.ensure_one()
        try:
            self.company_id._l10n_ge_edi_get_client().check_credentials()
        except RSgeError as error:
            message, notif_type = translate_rsge_error(self.env, error), "danger"
        else:
            message, notif_type = self.env._("RS.ge connection successful!"), "success"
        self.env.user._bus_send("simple_notification", {"type": notif_type, "message": message})
