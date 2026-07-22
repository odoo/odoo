from markupsafe import Markup

from odoo import fields, models

from odoo.addons.l10n_ge_edi.tools.rsge_client import RSgeError, translate_rsge_error


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ge_edi_un_id = fields.Char(string="RS.ge Un Id", readonly=True, copy=False)

    def action_l10n_ge_edi_fetch_un_id(self):
        """Resolve each partner's TIN (`vat`) to RS.ge's internal `un_id`, caching the result."""
        self.check_access("write")  # fail before making any RS.ge API calls, not after
        errors = []
        for company, partners in self.grouped("company_id").items():
            client = (company or self.env.company)._l10n_ge_edi_get_client()
            user_id = (company or self.env.company).sudo().l10n_ge_edi_user_id
            for partner in partners:
                if not partner.vat:
                    errors.append(self.env._("%s: set a VAT/TIN first.", partner.display_name))
                    continue
                try:
                    partner.l10n_ge_edi_un_id = client.get_un_id_from_tin(user_id=user_id, tin=partner.vat)
                except RSgeError as error:
                    errors.append(f"{partner.display_name}: {translate_rsge_error(self.env, error)}")
        if errors:
            message, notif_type = Markup("<br/>").join(errors), "danger"
        else:
            message, notif_type = (self.env._("RS.ge Un Id fetched successfully!"), "success")
        self.env.user._bus_send("simple_notification", {"type": notif_type, "message": message})
