# Copyright 2014 Tecnativa - Pedro M. Baeza
# Copyright 2020 Tecnativa - Manuel Calero
# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
from urllib import parse

from odoo import fields, models


class AddUrlWizard(models.TransientModel):
    _name = "ir.attachment.add_url"
    _description = "Wizard to add URL attachment"

    name = fields.Char(required=True)
    url = fields.Char("URL", required=True)

    def action_add_url(self):
        """Adds the URL with the given name as an ir.attachment record."""
        if not self.env.context.get("active_model"):
            return
        attachment_obj = self.env["ir.attachment"]
        for form in self:
            url = parse.urlparse(form.url)
            if not url.scheme:
                url = parse.urlparse("{}{}".format("http://", form.url))
            for active_id in self.env.context.get("active_ids", []):
                attachment = {
                    "name": form.name,
                    "type": "url",
                    "url": url.geturl(),
                    "res_id": active_id,
                    "res_model": self.env.context["active_model"],
                }
                attachment_obj.create(attachment)
        return {"type": "ir.actions.act_window_close"}
