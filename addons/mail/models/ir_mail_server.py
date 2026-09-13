import typing

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import email_normalize

if typing.TYPE_CHECKING:
    from .mail_template import MailTemplate
    from odoo.addons.bus.models.res_users import ResUsers

_debug = DebugLog(__name__)


class IrMail_Server(models.Model):
    _inherit = "ir.mail_server"
    _email_field = "smtp_user"

    mail_template_ids: MailTemplate = fields.One2many(
        comodel_name="mail.template",
        inverse_name="mail_server_id",
        string="Mail template using this mail server",
        readonly=True,
    )

    owner_user_id: ResUsers = fields.Many2one("res.users", "Owner", copy=False)

    owner_limit_time = fields.Datetime(copy=False)
    owner_limit_count = fields.Integer(copy=False)

    _unique_owner_user_id = models.Constraint(
        "UNIQUE(owner_user_id)",
        "owner_user_id must be unique",
    )

    def _get_active_usages(self) -> dict[int, list[str]]:
        usages_super = super()._get_active_usages()
        servers = self.with_context(active_test=False)
        for record in servers.filtered("mail_template_ids"):
            usages_super.setdefault(record.id, []).extend(
                self.env._("%s (Email Template)", template.display_name)
                if template.active
                else self.env._("%s (archived Email Template)", template.display_name)
                for template in record.mail_template_ids
            )
        return usages_super

    @api.model
    def _get_default_bounce_address(self) -> str:
        if self.env.company.bounce_email:
            _debug.logic("bounce_address", by="company", company=self.env.company.id)
            return self.env.company.bounce_email
        return super()._get_default_bounce_address()

    @api.model
    def _get_default_from_address(self) -> str:
        if default_from := self.env.company.default_from_email:
            _debug.logic("from_address", by="company", company=self.env.company.id)
            return default_from
        return super()._get_default_from_address()

    def _get_test_email_from(self) -> str:
        self.check_singleton()
        if mail_from := self._from_filter_sender():
            return mail_from
        if domain := self._from_filter_domain():
            alias_domains = self.env["mail.alias.domain"].sudo().search([])
            matching = next(
                (
                    alias_domain
                    for alias_domain in alias_domains
                    if self._match_from_filter(
                        alias_domain.default_from_email, self.from_filter
                    )
                ),
                False,
            )
            if matching:
                return matching.default_from_email
            return f"odoo@{domain}"
        return super()._get_test_email_from()

    @api.model
    def _filtered_mail_servers_fallback(self, servers: IrMail_Server) -> IrMail_Server:
        return servers.filtered(lambda s: not s.owner_user_id)

    def _get_domain_mail_servers_allowed(self) -> Domain:
        domain = super()._get_domain_mail_servers_allowed()
        domain &= Domain("owner_user_id", "=", False)
        return domain

    def _check_forced_mail_server(
        self, allow_archived: bool, smtp_from: str | None
    ) -> None:
        super()._check_forced_mail_server(allow_archived, smtp_from)

        if self.owner_user_id:
            _debug.logic(
                "personal_server_forced",
                server=self.id,
                owner=self.owner_user_id.id,
                active=self.active,
                current=self.owner_user_id.outgoing_mail_server_id == self,
            )
            if email_normalize(smtp_from) != email_normalize(self.from_filter):
                raise UserError(
                    _(
                        'The server "%s" cannot be forced as it belongs to a user.',
                        self.display_name,
                    )
                )
            if not self.active:
                raise UserError(
                    _(
                        'The server "%s" cannot be forced as it belongs to a user and is archived.',
                        self.display_name,
                    )
                )
            if self.owner_user_id.outgoing_mail_server_id != self:
                raise UserError(
                    _(
                        'The server "%s" cannot be forced as the owner does not use it anymore.',
                        self.display_name,
                    )
                )

    def _get_personal_mail_servers_limit(self) -> int:
        return self.env["ir.config_parameter"]._get_positive_int_param(
            "mail.server.personal.limit.minutes", 30
        )

    def _get_personal_mail_server_grace(self) -> int:
        return self.env["ir.config_parameter"]._get_positive_int_param(
            "mail.server.personal.setup.grace.minutes", 1440
        )
