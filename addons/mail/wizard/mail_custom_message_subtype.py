from odoo import fields, models
from odoo.addons.mail.tools.discuss import Store
from odoo.fields import Command


class MailCustomMessageSubtype(models.TransientModel):
    _name = "mail.custom.message.subtype"
    _description = "Custom Message Subtype"

    model = fields.Char()
    name = fields.Char(required=True, help="The name of the notification message")
    field_tracked = fields.Char(required=True, help="Get notified when this field is updated")
    value_update = fields.Char(
        help="The notification will be sent only if the tracked field changes "
        "to the selected value. If no value is selected, "
        "it will be sent for all updates."
    )
    domain = fields.Char(
        help="The notification will be sent only for records that match the selected domain."
    )
    default = fields.Boolean(
        string="Default Notification",
        default=True,
        help="Choose whether you want to be notified by default on all records you're following or "
        "if you prefer to manually subscribe to this notification.",
    )

    def create_subtype_with_options(self):
        """Save custom message subtype and return its ID."""
        subtype = self.env["mail.message.subtype"].create(
            {
                "name": self.name,
                "description": self.name,
                "default": self.default,
                "field_tracked": self.field_tracked,
                "value_update": self.value_update,
                "domain": self.domain,
                "user_ids": [Command.link(self.env.user.id)],
            }
        )
        return {
            "type": "ir.actions.act_window_close",
            "infos": {
                "store_data": Store().add(subtype, ["name", "field_tracked"]).get_result(),
                "subtype_id": subtype.id,
            },
        }
