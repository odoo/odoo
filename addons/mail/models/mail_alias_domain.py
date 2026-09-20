import logging
import typing
from collections.abc import Iterable
from typing import Literal, NamedTuple, Self

from odoo import _, api, exceptions, fields, models
from odoo.api import ValuesType
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, ormcache

if typing.TYPE_CHECKING:
    from odoo.addons.base.models.res_company import ResCompany

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class AliasDomainConfig(NamedTuple):
    ids: tuple[int, ...]
    names: tuple[str, ...]
    bounce_emails: tuple[str, ...]
    catchall_emails: tuple[str, ...]
    default_from_emails: tuple[str, ...]


CONFIG_FIELDS = (
    ("bounce_alias", "bounce_email", False),
    ("catchall_alias", "catchall_email", False),
    ("default_from", "default_from_email", True),
)


class MailAliasDomain(models.Model):
    _name = "mail.alias.domain"
    _description = "Email Domain"
    _order = "sequence ASC, id ASC"

    name = fields.Char(
        required=True,
        help="Email domain e.g. 'example.com' in 'odoo@example.com'",
    )
    company_ids: ResCompany = fields.One2many(
        comodel_name="res.company",
        inverse_name="alias_domain_id",
        string="Companies",
        help="Companies using this domain as default for sending mails",
    )
    sequence = fields.Integer(default=10)
    bounce_alias = fields.Char(
        default="bounce",
        required=True,
        help="Local-part of email used for Return-Path used when emails bounce e.g. "
        "'bounce' in 'bounce@example.com'",
    )
    bounce_email = fields.Char(compute="_compute_bounce_email")
    catchall_alias = fields.Char(
        default="catchall",
        required=True,
        help="Local-part of email used for Reply-To to catch answers e.g. "
        "'catchall' in 'catchall@example.com'",
    )
    catchall_email = fields.Char(compute="_compute_catchall_email")
    default_from = fields.Char(
        string="Default From Alias",
        default="notifications",
        help="Default from when it does not match outgoing server filters. Can be either "
        "a local-part e.g. 'notifications' either a complete email address e.g. "
        "'notifications@example.com' to override all outgoing emails.",
    )
    default_from_email = fields.Char(
        string="Default From",
        compute="_compute_default_from_email",
    )

    _bounce_email_uniques = models.Constraint(
        "UNIQUE(bounce_alias, name)",
        "Bounce emails should be unique",
    )
    _catchall_email_uniques = models.Constraint(
        "UNIQUE(catchall_alias, name)",
        "Catchall emails should be unique",
    )

    @api.depends("bounce_alias", "name")
    def _compute_bounce_email(self) -> None:
        self.bounce_email = ""
        for domain in self.filtered("bounce_alias"):
            domain.bounce_email = f"{domain.bounce_alias}@{domain.name}"

    @api.depends("catchall_alias", "name")
    def _compute_catchall_email(self) -> None:
        self.catchall_email = ""
        for domain in self.filtered("catchall_alias"):
            domain.catchall_email = f"{domain.catchall_alias}@{domain.name}"

    @api.depends("default_from", "name")
    def _compute_default_from_email(self) -> None:
        self.default_from_email = ""
        for domain in self.filtered("default_from"):
            if "@" in domain.default_from:
                domain.default_from_email = domain.default_from
            else:
                domain.default_from_email = f"{domain.default_from}@{domain.name}"

    @api.constrains("bounce_alias", "catchall_alias", "name")
    def _check_reserved_addresses_are_not_aliases(self) -> None:
        reserved = [
            email
            for email in self.mapped("bounce_email") + self.mapped("catchall_email")
            if email
        ]
        reserved_local_parts = [
            local_part
            for local_part in self.mapped("bounce_alias")
            + self.mapped("catchall_alias")
            if local_part
        ]
        existing = self.env["mail.alias"].search(
            Domain("alias_full_name", "in", reserved)
            | (
                Domain("alias_incoming_local", "=", True)
                & Domain("alias_name", "in", reserved_local_parts)
            ),
            limit=1,
        )
        if existing:
            document = existing.sudo()._alias_get_document(
                "owner"
            ) or existing.sudo()._alias_get_document("target")
            document_name = document.display_name if document else False
            if document_name:
                raise exceptions.ValidationError(
                    _(
                        "Bounce/Catchall '%(matching_alias_name)s' is already used by %(document_name)s. Choose another alias or change it on the other document.",
                        matching_alias_name=existing.display_name,
                        document_name=document_name,
                    )
                )
            raise exceptions.ValidationError(
                _(
                    "Bounce/Catchall '%(matching_alias_name)s' is already used. Choose another alias or change it on the linked model.",
                    matching_alias_name=existing.display_name,
                )
            )

    @api.constrains("bounce_alias", "catchall_alias", "name")
    def _check_reserved_addresses_are_unique(self) -> None:
        names = [name for name in set(self.mapped("name")) if name]
        if not names:
            return

        # The records being checked are read from the cache and the others
        # from the table: any fetch here would flush this model's pending
        # rows first, and the unique index would refuse before this check can
        # say why.
        def addresses(domain):
            return tuple(
                f"{alias}@{domain.name}" if alias else ""
                for alias in (domain.bounce_alias, domain.catchall_alias)
            )

        self.env.cr.execute(
            SQL(
                """
                SELECT id, name, bounce_alias, catchall_alias
                  FROM mail_alias_domain
                 WHERE name = ANY(%s) AND NOT (id = ANY(%s))
                """,
                names,
                list(self.ids),
            )
        )
        by_name = {}
        for sibling_id, name, bounce_alias, catchall_alias in self.env.cr.fetchall():
            for alias in (bounce_alias, catchall_alias):
                if alias:
                    by_name.setdefault(f"{alias}@{name}", []).append(sibling_id)
        for domain in self:
            for address in addresses(domain):
                if address:
                    by_name.setdefault(address, []).append(domain.id)

        for domain in self:
            for address in addresses(domain):
                if address and len(by_name.get(address, ())) > 1:
                    raise exceptions.ValidationError(
                        _(
                            "%(address)s is already reserved as a bounce or catchall "
                            "address. Every bounce and catchall address must be "
                            "distinct, including from each other.",
                            address=address,
                        )
                    )
            bounce, catchall = addresses(domain)
            if bounce and bounce == catchall:
                raise exceptions.ValidationError(
                    _(
                        "Bounce and catchall cannot both be %(address)s: a message to "
                        "it would only ever be treated as a bounce.",
                        address=domain.bounce_email,
                    )
                )

    @api.constrains("bounce_alias", "catchall_alias", "default_from")
    def _check_local_parts(self) -> None:
        for domain in self:
            for fname, is_email in (
                ("bounce_alias", False),
                ("catchall_alias", False),
                ("default_from", True),
            ):
                value = domain[fname]
                if not value:
                    continue
                if (
                    self.env["mail.alias"]._normalize_alias_name(
                        value, is_email=is_email
                    )
                    != value
                ):
                    raise exceptions.ValidationError(
                        _(
                            "%(field_label)s %(value)s is not a valid email local "
                            "part. Use unaccented lowercase latin characters, "
                            "without leading, trailing or repeated dots.",
                            field_label=domain._fields[fname].get_description(self.env)[
                                "string"
                            ],
                            value=value,
                        )
                    )

    @api.constrains("name")
    def _check_name(self) -> None:
        for domain in self:
            if not domain.name:
                raise exceptions.ValidationError(
                    _("You cannot assign an empty domain name.")
                )
            if self.env["mail.alias"]._normalize_alias_domain_name(domain.name) != (
                domain.name
            ):
                raise exceptions.ValidationError(
                    _(
                        "%(domain_name)s is not a usable domain name. Use unaccented "
                        "lowercase latin letters, digits and hyphens, with no leading, "
                        "trailing or repeated dot or hyphen.",
                        domain_name=domain.name,
                    )
                )

    @api.model
    @ormcache(cache="stable")
    def _get_config(self) -> AliasDomainConfig:
        domains = self.sudo().search([])
        _debug.perf.count("config_computed", domains=len(domains))
        return AliasDomainConfig(
            tuple(domains.ids),
            tuple(filter(None, domains.mapped("name"))),
            tuple(filter(None, domains.mapped("bounce_email"))),
            tuple(filter(None, domains.mapped("catchall_email"))),
            tuple(filter(None, domains.mapped("default_from_email"))),
        )

    @api.model
    def _get_alias_domain_names(self) -> tuple[str, ...]:
        return self._get_config().names

    @api.model
    def _get_bounce_emails(self) -> tuple[str, ...]:
        return self._get_config().bounce_emails

    @api.model
    def _get_catchall_emails(self) -> tuple[str, ...]:
        return self._get_config().catchall_emails

    @api.model
    def _get_default_from_emails(self) -> tuple[str, ...]:
        return self._get_config().default_from_emails

    @api.model
    def _get_company_for_catchall_emails(self, emails: Iterable[str]) -> ResCompany:
        wanted = {email for email in emails if email}
        if not wanted:
            return self.env["res.company"]
        for domain in self.browse(self._get_config().ids).sudo():
            if domain.catchall_email in wanted and domain.company_ids:
                return domain.company_ids[:1]
        return self.env["res.company"]

    @api.model
    def _get_allowed_domains(self) -> frozenset[str]:
        configured = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail.catchall.domain.allowed")
            or ""
        )
        allowed = set(filter(None, configured.split(",")))
        if allowed:
            allowed.update(self._get_config().names)
        return frozenset(allowed)

    @api.model
    def _get_reserved_local_parts(self) -> frozenset[str]:
        config = self._get_config()
        return frozenset(
            email.partition("@")[0]
            for email in config.bounce_emails + config.catchall_emails
            if email
        )

    @api.model
    def _get_default_domain(self) -> Self:
        return self.browse(self._get_config().ids[:1])

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        for vals in vals_list:
            self._update_configuration(vals)

        was_unconfigured = not self.search_count([], limit=1)

        alias_domains = super().create(vals_list)
        self.env.registry.clear_cache("stable")
        _debug.lifecycle(
            "create", domains=alias_domains.ids, was_unconfigured=was_unconfigured
        )

        if was_unconfigured and alias_domains:
            default = self._get_default_domain()
            self.env["res.company"].with_context(active_test=False).search(
                [("alias_domain_id", "=", False)]
            ).alias_domain_id = default.id
            self.env["mail.alias"].sudo().search(
                [("alias_domain_id", "=", False)]
            ).alias_domain_id = default.id

        return alias_domains

    def write(self, vals: ValuesType) -> Literal[True]:
        self._update_configuration(vals)
        ret = super().write(vals)
        self.env.registry.clear_cache("stable")
        _debug.lifecycle("write", domains=self.ids, fields=list(vals))
        return ret

    def unlink(self) -> Literal[True]:
        self.env.registry.clear_cache("stable")
        _debug.lifecycle("unlink", domains=self.ids)
        return super().unlink()

    @api.ondelete(at_uninstall=False)
    def _warn_when_a_company_loses_its_domain(self) -> None:
        if used := self.filtered("company_ids"):
            _logger.warning(
                "Deleting alias domain(s) %s leaves %s with no email domain: "
                "outgoing mail from them carries no Return-Path and no default From "
                "until one is configured.",
                ", ".join(used.mapped("name")),
                ", ".join(used.company_ids.sorted("id").mapped("display_name")),
            )

    @api.constrains("default_from", "name")
    def _check_default_from_not_used_by_users(self) -> None:
        addresses = [
            address for address in self.mapped("default_from_email") if address
        ]
        if not addresses:
            return

        servers = (
            self.env["ir.mail_server"]
            .sudo()
            .search([("owner_user_id", "!=", False), ("from_filter", "!=", False)])
        )
        IrMailServer = self.env["ir.mail_server"]
        for server in servers:
            from_filter = IrMailServer._from_filter_index(server.from_filter)
            for address in addresses:
                if from_filter.matches(address):
                    raise exceptions.ValidationError(
                        _(
                            "%(address)s is the sending address of %(user_name)s's "
                            "personal mail server. Choose another default from, or "
                            "remove that server first.",
                            address=address,
                            user_name=server.owner_user_id.display_name,
                        )
                    )

    @api.model
    def _update_configuration(self, config_values: dict) -> None:
        Alias = self.env["mail.alias"]
        if name := config_values.get("name"):
            config_values["name"] = Alias._normalize_alias_domain_name(name) or name
        for fname, _email_fname, is_email in CONFIG_FIELDS:
            if value := config_values.get(fname):
                config_values[fname] = Alias._normalize_alias_name(
                    value, is_email=is_email
                )

    @api.model
    def _normalize_allowed_domains(self, allowed_domains: str) -> str:
        Alias = self.env["mail.alias"]
        seen, value = set(), []
        for candidate in allowed_domains.split(","):
            if not candidate.strip():
                continue
            domain = Alias._normalize_alias_domain_name(candidate)
            if not domain:
                raise exceptions.ValidationError(
                    _(
                        "%(domain)s is not a valid domain name for "
                        "`mail.catchall.domain.allowed`.",
                        domain=candidate.strip(),
                    )
                )
            if domain not in seen:
                seen.add(domain)
                value.append(domain)
        if not value:
            raise exceptions.ValidationError(
                _(
                    "Value %(allowed_domains)s for `mail.catchall.domain.allowed` cannot be validated.\n"
                    "It should be a comma separated list of domains e.g. example.com,example.org.",
                    allowed_domains=allowed_domains,
                )
            )
        return ",".join(value)

    @api.model
    def _get_alias_emails(self, email_list: list[str]) -> list[str]:
        split = [(e, *e.partition("@")[::2]) for e in email_list if e and "@" in e]
        if not split:
            return []
        config = self._get_config()
        addresses = self.env["mail.alias"]._get_alias_addresses()
        local_alias_names = addresses.local_names
        aliases = addresses.full_names.union(
            config.bounce_emails, config.catchall_emails, config.default_from_emails
        )
        allowed_domains = self._get_allowed_domains()

        res, seen = [], set()
        for email, local_part, domain in split:
            if email in seen:
                continue
            if email in aliases or (
                local_part in local_alias_names
                and (not allowed_domains or domain in allowed_domains)
            ):
                seen.add(email)
                res.append(email)
        _debug.logic(
            "alias_emails",
            asked=len(split),
            matched=len(res),
            allowed_domains=len(allowed_domains),
        )
        return res

    @api.model
    def _migrate_icp_to_domain(self) -> Self:
        Icp = self.env["ir.config_parameter"].sudo()
        raw_name = Icp.get_param("mail.catchall.domain")
        if not raw_name:
            return self.browse()

        alias_domain = self.env["mail.alias"]._normalize_alias_domain_name(raw_name)
        if not alias_domain:
            _debug.logic("icp_migration_skipped", reason="unusable_domain")
            _logger.warning(
                "Ignoring `mail.catchall.domain` = %r: not a usable domain name. "
                "No alias domain was created; configure one in Settings.",
                raw_name,
            )
            return self.browse()

        if existing := self.search([("name", "=", alias_domain)], limit=1):
            _debug.logic("icp_migration", domain=existing.id, by="existing")
            return existing
        _debug.lifecycle("icp_migration", name=alias_domain, by="created")
        return self.create(
            {
                "bounce_alias": Icp.get_param("mail.bounce.alias") or "bounce",
                "catchall_alias": Icp.get_param("mail.catchall.alias") or "catchall",
                "default_from": Icp.get_param("mail.default.from") or "notifications",
                "name": alias_domain,
            }
        )
