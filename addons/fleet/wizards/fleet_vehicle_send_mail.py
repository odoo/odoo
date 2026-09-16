from odoo import _, api, fields, models


class FleetVehicleSendMail(models.TransientModel):
    _name = "fleet.vehicle.send.mail"
    _inherit = ["mixin.mail.composer"]
    _description = "Send mails to Drivers"

    vehicle_ids = fields.Many2many(
        comodel_name="resource.asset",
        string="Vehicles",
        required=True,
        domain="[('is_vehicle', '=', True)]",
    )
    author_id = fields.Many2one(
        comodel_name="res.partner",
        default=lambda self: self.env.user.partner_id.id,
        required=True,
    )
    template_id = fields.Many2one(
        domain=lambda self: [
            ("model_id", "=", self.env["ir.model"]._get("resource.asset").id)
        ]
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="fleet_vehicle_mail_compose_message_ir_attachments_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Attachments",
        bypass_search_access=True,
    )

    @api.depends("subject")
    def _compute_render_model(self):
        self.render_model = "resource.asset"

    @api.onchange("template_id")
    def _onchange_template_id(self):
        self.attachment_ids = self.template_id.attachment_ids

    def action_send(self):
        self.check_singleton()
        without_emails = self.vehicle_ids.operator_id.partner_id.filtered(
            lambda partner: not partner.email
        )
        if without_emails:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "danger",
                    "message": _(
                        "The following vehicle drivers are missing an email address: %s.",
                        ", ".join(without_emails.mapped("name")),
                    ),
                },
            }

        if self.template_id:
            subjects = self._render_field(field="subject", res_ids=self.vehicle_ids.ids)
            bodies = self._render_field(field="body", res_ids=self.vehicle_ids.ids)
        else:
            subjects = {vehicle.id: self.subject for vehicle in self.vehicle_ids}
            bodies = {vehicle.id: self.body for vehicle in self.vehicle_ids}

        for vehicle in self.vehicle_ids:
            vehicle.message_post(
                author_id=self.author_id.id,
                body=bodies[vehicle.id],
                email_layout_xmlid="mail.mail_notification_light",
                message_type="comment",
                partner_ids=vehicle.operator_id.partner_id.ids,
                subject=subjects[vehicle.id],
            )
        # Nothing to do next: an action method answering None closes the dialog,
        # and the branch above returns a notification instead. Spelled out
        # because the two exits returning different kinds of thing is the point.
        return None

    def action_save_as_template(self):
        model = self.env["ir.model"]._get("resource.asset")
        template_name = _("Vehicle: Mass mail drivers")
        template = self.env["mail.template"].create(
            {
                "name": template_name,
                "subject": self.subject or False,
                "body_html": self.body or False,
                "model_id": model.id,
                "use_default_to": True,
            }
        )

        if self.attachment_ids:
            attachments = (
                self.env["ir.attachment"]
                .sudo()
                .browse(self.attachment_ids.ids)
                .filtered(lambda a: a.create_uid.id == self.env.uid)
            )
            if attachments:
                attachments.write({"res_model": template._name, "res_id": template.id})
            template.attachment_ids |= self.attachment_ids

        self.write({"template_id": template.id})

        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_id": template.id,
            "res_model": "mail.template",
            "target": "new",
        }
