from odoo import _, api, models, modules

SMS_SUBKEY = "sms"


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _activity_bucket_subkeys(self, model_name, res_ids):
        if model_name != "mailing.mailing":
            return super()._activity_bucket_subkeys(model_name, res_ids)
        mailings = (
            self.env["mailing.mailing"].browse(res_ids).with_context(active_test=False)
        )
        return {
            mailing.id: SMS_SUBKEY
            for mailing in mailings
            if mailing.mailing_type == "sms"
        }

    @api.model
    def _apply_activity_bucket_subkey(self, group, model_name, subkey, res_ids):
        group = super()._apply_activity_bucket_subkey(
            group, model_name, subkey, res_ids
        )
        if model_name != "mailing.mailing":
            return group
        if subkey == SMS_SUBKEY:
            group["name"] = _("SMS Marketing")
            group["icon"] = modules.Manifest.for_addon("mass_mailing_sms").icon
        group["domain"] = [
            ("active", "in", [True, False]),
            ("id", "in", res_ids),
        ]
        return group
