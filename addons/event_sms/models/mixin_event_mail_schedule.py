from odoo import fields, models


class MixinEventMailSchedule(models.AbstractModel):
    """Add SMS as a channel for event communications."""

    _inherit = "mixin.event.mail.schedule"

    notification_type = fields.Selection(selection_add=[("sms", "SMS")])
    template_ref = fields.Reference(
        selection_add=[("sms.template", "SMS")],
        ondelete={"sms.template": "cascade"},
    )

    def _compute_notification_type(self):
        super()._compute_notification_type()
        sms_schedulers = self.filtered(
            lambda scheduler: (
                scheduler.template_ref
                and scheduler.template_ref._name == "sms.template"
            )
        )
        sms_schedulers.notification_type = "sms"

    def _template_model_by_notification_type(self):
        info = super()._template_model_by_notification_type()
        info["sms"] = "sms.template"
        return info
