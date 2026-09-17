from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import consteq

_debug = DebugLog(__name__)


class DocumentsAccess(models.Model):
    _name = "document.access"
    _description = "Document / Partner"
    _log_access = False

    document_id = fields.Many2one(
        comodel_name="document.document",
        index=True,
        required=True,
        ondelete="cascade",
        bypass_search_access=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        index=True,
        required=True,
        ondelete="cascade",
    )
    role = fields.Selection(
        selection=[("view", "Viewer"), ("edit", "Editor")],
        index=True,
        required=False,
    )
    last_access_date = fields.Datetime(
        string="Last Accessed On",
        required=False,
    )
    expiration_date = fields.Datetime(
        string="Expiration",
        index=True,
    )

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
                _debug.logic("member_refused", reason="public_partner", access=access)
                raise ValidationError(_("This user can not be member."))

    def _prepare_create_values(self, vals_list: list[dict]) -> list[dict]:
        vals_list = super()._prepare_create_values(vals_list)
        documents = self.env["document.document"].browse(
            [vals["document_id"] for vals in vals_list]
        )
        documents.check_access("write")
        _debug.lifecycle("access_create", count=len(vals_list), documents=documents)
        return vals_list

    def write(self, vals: dict) -> bool:
        if "partner_id" in vals or "document_id" in vals:
            _debug.logic("access_write_refused", reason="identity_change")
            raise AccessError(_("Access documents and partners cannot be changed."))

        self.document_id.check_access("write")
        _debug.lifecycle("access_write", access=self, fields=sorted(vals))
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
        _debug.lifecycle(
            "access_expired",
            expired=len(expired),
            demoted=len(visited),
            removed=len(expired) - len(visited),
        )
        visited.write({"role": False, "expiration_date": False})
        (expired - visited).unlink()
        return len(expired), len(expired) == limit

    @api.model
    def _recent_retention_days(self) -> int:
        return int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("document.recent_retention_days", 365)
        )

    @api.autovacuum
    def _gc_recent(self) -> tuple[int, bool]:
        retention_days = self._recent_retention_days()
        if retention_days <= 0:
            return 0, False
        limit = 10000
        stale = self.search(
            [
                ("role", "=", False),
                ("expiration_date", "=", False),
                (
                    "last_access_date",
                    "<",
                    fields.Datetime.subtract(
                        fields.Datetime.now(), days=retention_days
                    ),
                ),
            ],
            limit=limit,
        )
        removed = len(stale)
        _debug.lifecycle(
            "access_recent_gc", removed=removed, retention_days=retention_days
        )
        stale.unlink()
        return removed, removed == limit

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
            _debug.logic("member_invite_refused", access=self)
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
            _debug.logic("signup_token_refused", reason="unavailable", member=member_id)
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
            _debug.logic("signup_token_refused", reason="non_ascii", member=member_id)
            return False
        if not consteq(member_sudo._get_member_signup_token(), token):
            _debug.logic("signup_token_refused", reason="mismatch", member=member_id)
            return False
        _debug.logic("signup_token_accepted", member=member_id)
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
