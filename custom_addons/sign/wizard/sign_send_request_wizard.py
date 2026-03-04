from odoo import api, fields, models


class SignSendRequestWizard(models.TransientModel):
    _name = "sign.request.send.wizard"
    _description = "Send Signature Request"

    request_id = fields.Many2one(
        comodel_name="sign.request",
        required=True,
        ondelete="cascade",
    )
    signer_ids = fields.Many2many(
        comodel_name="sign.request.item",
        relation="sign_send_request_wizard_item_rel",
        column1="wizard_id",
        column2="item_id",
        string="Signers",
        required=True,
        domain="[('sign_request_id', '=', request_id)]",
    )
    subject = fields.Char(required=True)
    message = fields.Text()

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        request_id = self.env.context.get("default_request_id")
        request = self.env["sign.request"].browse(request_id)
        if request:
            values.setdefault("request_id", request.id)
            values.setdefault("signer_ids", [(6, 0, request.request_item_ids.ids)])
            values.setdefault(
                "subject",
                "Signature request: %s" % (request.name or request.reference),
            )
            values.setdefault(
                "message",
                request.message or "Please review and sign the document.",
            )
        return values

    def action_send(self):
        self.ensure_one()
        self.request_id.action_sent(
            signer_ids=self.signer_ids.ids,
            subject=self.subject,
            message=self.message,
        )
        return {"type": "ir.actions.act_window_close"}

