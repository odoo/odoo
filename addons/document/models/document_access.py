from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import consteq


class DocumentsAccess(models.Model):
    _name = "document.access"
    _description = "Document / Partner"
    _log_access = False

    document_id = fields.Many2one(
        "document.document",
        required=True,
        bypass_search_access=True,
        index=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="cascade",
        index=True,
    )
    role = fields.Selection(
        [("view", "Viewer"), ("edit", "Editor")],
        required=False,
        index=True,
    )
    last_access_date = fields.Datetime("Last Accessed On", required=False)
    expiration_date = fields.Datetime("Expiration", index=True)

    _unique_document_access_partner = models.Constraint(
        "unique(document_id, partner_id)",
        "This partner is already set on this document.",
    )
    _role_or_last_access_date = models.Constraint(
        "check (role IS NOT NULL or last_access_date IS NOT NULL)",
        "NULL roles must have a set last_access_date",
    )

    @api.constrains("partner_id", "role")
    def _check_partner_id(self) -> None:
        public_partner = self.env.ref("base.public_user").partner_id
        for access in self:
            if access.role and access.partner_id == public_partner:
                raise ValidationError(_("This user can not be member."))

    def _prepare_create_values(self, vals_list: list[dict]) -> list[dict]:
        vals_list = super()._prepare_create_values(vals_list)
        documents = self.env["document.document"].browse(
            [vals["document_id"] for vals in vals_list]
        )
        documents.check_access("write")
        return vals_list

    def write(self, vals: dict) -> bool:
        if "partner_id" in vals or "document_id" in vals:
            raise AccessError(_("Access documents and partners cannot be changed."))

        self.document_id.check_access("write")
        return super().write(vals)

    @api.autovacuum
    def _gc_expired(self) -> tuple[int, bool]:
        limit = 1000
        expired = self.search(
            [("expiration_date", "<=", fields.Datetime.now())], limit=limit
        )
        if not expired:
            return 0, False
        visited = expired.filtered("last_access_date")
        visited.write({"role": False, "expiration_date": False})
        (expired - visited).unlink()
        return len(expired), len(expired) == limit

    def _is_signup_available(self) -> bool:
        return (
            self.env["res.users"].sudo()._get_signup_invitation_scope() == "b2c"
            and self.role
            and (
                not self.expiration_date or self.expiration_date > fields.Datetime.now()
            )
            and not self.partner_id.with_context(active_test=False).user_ids
        )

    def _get_member_signup_token(self) -> str:
        self.check_singleton()
        if not self._is_signup_available():
            raise UserError(_("Cannot invite this member."))

        return tools.hmac(
            self.env(su=True),
            "documents-member-signup-token",
            (self.id, self.partner_id.id),
        )

    @api.model
    def _get_member_from_token(
        self, member_id: int, token: str
    ) -> DocumentsAccess | bool:
        member_sudo = self.browse(member_id).sudo().exists()
        if not member_sudo or not member_sudo._is_signup_available():
            return False
        # `consteq` is `hmac.compare_digest`, which raises TypeError on a `str`
        # holding non-ASCII. `token` is the raw, public, attacker-controlled
        # `member_signup_token` query parameter, so without this guard any
        # non-ASCII value turned `/documents/<anything>` into an
        # unauthenticated HTTP 500 -- no valid document token needed, only a
        # `document.access` id, which is a small guessable integer. A real
        # token is `tools.hmac` output (hex), so non-ASCII simply never matches.
        # This is the same guard `document.ShareRoute._from_access_token`
        # already applies to `document_token`; this call site was missed.
        if not isinstance(token, str) or not token.isascii():
            return False
        if not consteq(member_sudo._get_member_signup_token(), token):
            return False
        return member_sudo

    @api.model
    def _get_signup_url(
        self,
        member_id: int,
        member_signup_token: str,
        access_token: str,
        redirect_url: str,
    ) -> str:
        if not member_id or not member_signup_token or not access_token:
            return ""

        member_sudo = self._get_member_from_token(member_id, member_signup_token)
        if not member_sudo:
            return ""

        member_sudo.partner_id.signup_get_auth_param()
        return member_sudo.partner_id._get_signup_url_for_action(url=redirect_url)[
            member_sudo.partner_id.id
        ]
