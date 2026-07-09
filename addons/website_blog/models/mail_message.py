from odoo import models


class MailMessage(models.Model):
    _name = "mail.message"
    _inherit = ["mail.message", "website.ugc.mixin"]

    def _portal_message_format(self, properties_names, options=None):
        vals_list = super()._portal_message_format(properties_names, options=options)

        for values in vals_list:
            if values.get("model") == "blog.post" and values.get("body"):
                values["body"] = self._add_rel_to_links(
                    values["body"], ["ugc", "nofollow"]
                )
        return vals_list
