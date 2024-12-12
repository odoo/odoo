from odoo import fields, models
from odoo.exceptions import UserError
from odoo.addons.mail.tools.parser import parse_res_ids

class MailFollowersEdit(models.TransientModel):
    """Wizard to edit partners (or channels) to add/remove them to/from followers list."""

    _description = "Followers edit wizard"

    res_model = fields.Char(
        "Related Document Model", required=True, help="Model of the followed resource"
    )
    res_ids = fields.Char("Related Document IDs", help="Ids of the followed resources")
    operation = fields.Selection(
        [
            ("add", "Add"),
            ("remove", "Remove"),
        ],
        string="Operation",
        required=True,
        default="add",
    )
    partner_ids = fields.Many2many("res.partner", required=True, string="Followers")

    def edit_followers(self):
        for wizard in self:
            res_ids = parse_res_ids(wizard.res_ids, self.env)
            documents = self.env[wizard.res_model].browse(res_ids)
            for document in documents:
                if wizard.operation == "remove":
                    document.message_unsubscribe(partner_ids=wizard.partner_ids.ids)
                else:
                    # filter partner_ids to get the new followers, to avoid replicate following partners
                    new_partners = wizard.partner_ids - document.sudo().message_partner_ids
                    if not new_partners:
                        continue
                    document.message_subscribe(partner_ids=new_partners.ids)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "success",
                    "message": self.env._("✅ Followers added") if wizard.operation == "add" else self.env._("✅ Followers removed"),
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
