import secrets

from odoo import api, fields, models


class SignRequestItem(models.Model):
    _name = "sign.request.item"
    _description = "Sign Request Item"
    _order = "id"

    sign_request_id = fields.Many2one(
        comodel_name="sign.request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        ondelete="set null",
        index=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("completed", "Completed"),
            ("refused", "Refused"),
        ],
        default="draft",
        required=True,
    )
    signing_date = fields.Datetime(copy=False)
    access_token = fields.Char(required=True, copy=False, readonly=True, index=True)
    signer_email = fields.Char()
    signer_name = fields.Char()
    refusal_reason = fields.Text()
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="sign_request_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )

    _access_token_unique = models.Constraint(
        "UNIQUE(access_token)",
        "Signer access token must be unique.",
    )

    @api.model
    def _generate_unique_access_token(self):
        token = secrets.token_urlsafe(32)
        while self.sudo().search_count([("access_token", "=", token)]):
            token = secrets.token_urlsafe(32)
        return token

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            if not self.signer_email:
                self.signer_email = self.partner_id.email
            if not self.signer_name:
                self.signer_name = self.partner_id.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("access_token"):
                vals["access_token"] = self._generate_unique_access_token()
        records = super().create(vals_list)
        for item in records:
            updates = {}
            if item.partner_id and not item.signer_email and item.partner_id.email:
                updates["signer_email"] = item.partner_id.email
            if item.partner_id and not item.signer_name and item.partner_id.name:
                updates["signer_name"] = item.partner_id.name
            if updates:
                item.write(updates)
        return records

    def _get_sign_link(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", default="")
        return "%s/sign/document/%s" % (base_url.rstrip("/"), self.access_token)

    def action_draft(self):
        self.write(
            {
                "state": "draft",
                "signing_date": False,
                "refusal_reason": False,
            }
        )
        return True

    def action_sent(self):
        self.write({"state": "sent"})
        return True

    def action_completed(self):
        requests_to_finalize = self.env["sign.request"]
        now = fields.Datetime.now()
        for item in self:
            item.write(
                {
                    "state": "completed",
                    "signing_date": now,
                    "refusal_reason": False,
                }
            )
            request = item.sign_request_id
            if request and request.state in ("draft", "sent"):
                total = len(request.request_item_ids)
                done = len(request.request_item_ids.filtered(lambda rec: rec.state == "completed"))
                if total and done == total:
                    requests_to_finalize |= request
        for request in requests_to_finalize:
            request.action_signed()
        return True

    def action_refused(self, refusal_reason=None):
        impacted_requests = self.env["sign.request"]
        for item in self:
            item.write(
                {
                    "state": "refused",
                    "refusal_reason": refusal_reason or False,
                }
            )
            if item.sign_request_id:
                impacted_requests |= item.sign_request_id
        for request in impacted_requests:
            if request.state not in ("refused", "signed", "canceled"):
                request.action_refused(refusal_reason)
        return True
