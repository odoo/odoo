import base64
import copy
import datetime
import email.policy
import functools
import logging
import re
import smtplib
import ssl
from collections.abc import Callable, Iterable
from contextlib import suppress
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, make_msgid
from socket import gaierror
from typing import TYPE_CHECKING, Any, NamedTuple, Self
from weakref import WeakKeyDictionary

import idna
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import load_pem_x509_certificates
from OpenSSL.crypto import Error as SSLCryptoError
from OpenSSL.SSL import VERIFY_FAIL_IF_NO_PEER_CERT, VERIFY_PEER
from OpenSSL.SSL import Error as SSLError
from urllib3.contrib.pyopenssl import PyOpenSSLContext, get_subj_alt_name
from urllib3.util.ssl_match_hostname import CertificateError, match_hostname

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.libs.email import extract_rfc2822_addresses
from odoo.tools import (
    email_domain_extract,
    email_domain_normalize,
    email_normalize,
    encapsulate_email,
    human_size,
)

if TYPE_CHECKING:
    from .mail_template import MailTemplate
    from odoo.addons.bus.models.res_users import ResUsers

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)
_test_logger = logging.getLogger("odoo.tests")

SMTP_TIMEOUT = 60

IMPLICIT_TLS_ENCRYPTIONS = frozenset({"ssl", "ssl_strict"})
STARTTLS_ENCRYPTIONS = frozenset({"starttls", "starttls_strict"})
VERIFIED_ENCRYPTIONS = frozenset({"ssl_strict", "starttls_strict"})

DOMAIN_PATTERN = re.compile(
    r"^(?!-)[^\W_](?:[\w-]*[^\W_])?(?:\.(?!-)[^\W_](?:[\w-]*[^\W_])?)*$",
    re.UNICODE,
)

CONNECTION_TEST_ERRORS = (
    (UnicodeError, lambda e: _("Invalid server name!\n %s", e)),
    (
        (TimeoutError, gaierror),
        lambda e: _(
            "No response received. Check server address and port number.\n %s", e
        ),
    ),
    (
        ConnectionError,
        lambda e: _(
            "Could not establish a connection. Check the port number, and that the "
            "server is reachable and accepts connections from this machine.\n %s",
            e,
        ),
    ),
    (
        smtplib.SMTPServerDisconnected,
        lambda e: _(
            "The server has closed the connection unexpectedly. Check configuration served on this port number.\n %s",
            e,
        ),
    ),
    (
        smtplib.SMTPResponseException,
        lambda e: _("Server replied with following exception:\n %s", e),
    ),
    (
        smtplib.SMTPNotSupportedError,
        lambda e: _("An option is not supported by the server:\n %s", e),
    ),
    (
        smtplib.SMTPException,
        lambda e: _(
            "An SMTP exception occurred. Check port number and connection security type.\n %s",
            e,
        ),
    ),
    (
        CertificateError,
        lambda e: _(
            "An SSL exception occurred. Check connection security type.\n CertificateError: %s",
            e,
        ),
    ),
    (
        (ssl.SSLError, SSLError),
        lambda e: _(
            "An SSL exception occurred. Check connection security type.\n %s", e
        ),
    ),
    (
        OSError,
        lambda e: _(
            "The connection to the server failed. Check the server address, the port "
            "number and your network.\n %s",
            e,
        ),
    ),
)

CERTIFICATE_LOAD_ERRORS = (
    SSLCryptoError,
    SSLError,
    ssl.SSLError,
    ValueError,
    TypeError,
)


class MailDeliveryError(Exception):
    def __str__(self) -> str:
        return "\n".join(str(arg) for arg in self.args)


class OutgoingEmailError(UserError):
    def __init__(self, message: str, code: str) -> None:
        self.code = code
        super().__init__(message)


def _log_smtp_debug(*args: Any) -> None:
    _logger.debug("%s", " ".join(str(arg) for arg in args))


def _check_hostname_callback(
    cnx: Any,
    x509: Any,
    err_no: int,
    err_depth: int,
    return_code: int,
    *,
    hostname: str,
) -> bool:
    if err_no:
        return False

    if err_depth == 0:
        match_hostname({"subjectAltName": get_subj_alt_name(x509)}, hostname)

    return True


class _SmtpTransport(NamedTuple):
    server: str | None
    port: int | None
    user: str | None
    password: str | None
    encryption: str | None
    debug: bool
    from_filter: str | None
    ssl_context: ssl.SSLContext | PyOpenSSLContext | None
    login_server: IrMail_Server
    timeout: float | None = SMTP_TIMEOUT


class _FromFilter(NamedTuple):
    emails: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    unparsed: tuple[str, ...] = ()

    @property
    def unrestricted(self) -> bool:
        return not (self.emails or self.domains or self.unparsed)

    def matches(self, email_from: str | bool) -> bool:
        if self.unrestricted:
            return True
        normalized = email_normalize(email_from)
        return bool(normalized) and (
            normalized in self.emails
            or email_domain_extract(normalized) in self.domains
        )

    def sender(self) -> str | None:
        return self.emails[0] if self.emails else None

    def domain(self) -> str | None:
        return self.domains[0] if self.domains else None


class _SmtpSessionContext(NamedTuple):
    from_filter: str | bool = False
    smtp_from: str | bool = False
    mail_server_id: int | None = None


_SESSION_CONTEXTS: WeakKeyDictionary[smtplib.SMTP, _SmtpSessionContext] = (
    WeakKeyDictionary()
)


class IrMail_Server(models.Model):
    _name = "ir.mail_server"
    _description = "Mail Server"
    _order = "sequence, id"
    _allow_sudo_commands = False
    _email_field = "smtp_user"

    NO_VALID_RECIPIENT = "no_valid_recipient"
    NO_FOUND_FROM = "no_found_from"
    NO_FOUND_SMTP_FROM = "no_found_smtp_from"
    NO_VALID_FROM = "no_valid_from"

    name = fields.Char(
        index=True,
        required=True,
    )
    from_filter = fields.Char(
        string="FROM Filtering",
        help="Comma-separated list of addresses or domains for which this server can be used.\n"
        'e.g.: "notification@odoo.com" or "odoo.com"',
    )
    smtp_host = fields.Char(
        string="SMTP Server",
        help="Hostname or IP of SMTP server",
    )
    smtp_port = fields.Integer(
        string="SMTP Port",
        default=25,
        help="SMTP Port. Usually 465 for SSL, and 25 or 587 for other cases.",
    )
    smtp_authentication = fields.Selection(
        selection=[
            ("login", "Username"),
            ("certificate", "SSL Certificate"),
            ("cli", "Command Line Interface"),
        ],
        string="Authenticate with",
        default="login",
        required=True,
    )
    smtp_authentication_info = fields.Text(
        string="Authentication Info",
        compute="_compute_smtp_authentication_info",
    )
    smtp_user = fields.Char(
        string="Username",
        groups="base.group_system",
        help="Optional username for SMTP authentication",
    )
    smtp_pass = fields.Char(
        string="Password",
        groups="base.group_system",
        help="Optional password for SMTP authentication",
    )
    smtp_encryption = fields.Selection(
        selection=[
            ("none", "None"),
            ("starttls_strict", "TLS (STARTTLS), encryption and validation"),
            ("starttls", "TLS (STARTTLS), encryption only"),
            ("ssl_strict", "SSL/TLS, encryption and validation"),
            ("ssl", "SSL/TLS, encryption only"),
        ],
        string="Connection Encryption",
        default="none",
        required=True,
        help="Choose the connection encryption scheme:\n"
        "- None: SMTP sessions are done in cleartext.\n"
        "- TLS (STARTTLS): TLS encryption is requested at start of SMTP session (Recommended)\n"
        "- SSL/TLS: SMTP sessions are encrypted with SSL/TLS through a dedicated port (default: 465)\n"
        "\n"
        "Choose an additional variant for SSL or TLS:\n"
        "- encryption and validation: encrypt the data and authenticate the server using its SSL certificate (Recommended)\n"
        "- encryption only: encrypt the data but skip server authentication",
    )
    smtp_ssl_certificate = fields.Binary(
        string="SSL Certificate",
        attachment=False,
        groups="base.group_system",
        help="SSL certificate used for authentication",
    )
    smtp_ssl_private_key = fields.Binary(
        string="SSL Private Key",
        attachment=False,
        groups="base.group_system",
        help="SSL private key used for authentication",
    )
    smtp_debug = fields.Boolean(
        string="Debugging",
        help="If enabled, the SMTP session transcript is written to the Odoo "
        "log at DEBUG level, from the first command after the connection is "
        "open (this is very verbose and includes the authentication exchange!). "
        "DEBUG logging must also be enabled for it to appear, e.g. "
        "--log-handler=odoo.addons.mail.models.ir_mail_server:DEBUG",
    )
    max_email_size = fields.Float()
    sequence = fields.Integer(
        string="Priority",
        default=10,
        help="When no specific mail server is requested for a mail, the highest priority one "
        "is used. Default priority is 10 (smaller number = higher priority)",
    )
    active = fields.Boolean(default=True)
    mail_template_ids: MailTemplate = fields.One2many(
        comodel_name="mail.template",
        inverse_name="mail_server_id",
        string="Mail template using this mail server",
        readonly=True,
    )
    owner_user_id: ResUsers = fields.Many2one(
        comodel_name="res.users",
        string="Owner",
        copy=False,
    )
    owner_limit_time = fields.Datetime(copy=False)
    owner_limit_count = fields.Integer(copy=False)

    _unique_owner_user_id = models.Constraint(
        "UNIQUE(owner_user_id)",
        "owner_user_id must be unique",
    )
    _certificate_requires_tls = models.Constraint(
        "CHECK(smtp_encryption != 'none' OR smtp_authentication != 'certificate')",
        "Certificate-based authentication requires a TLS transport",
    )
    _host_required_unless_cli = models.Constraint(
        "CHECK(NOT active OR smtp_authentication = 'cli' "
        "OR COALESCE(smtp_host, '') != '')",
        "An outgoing mail server needs an SMTP server address unless it takes its "
        "transport from the command-line configuration. Archive it instead if it "
        "is not meant to deliver.",
    )
    _smtp_port_in_range = models.Constraint(
        "CHECK(smtp_authentication = 'cli' OR smtp_port BETWEEN 1 AND 65535)",
        "The SMTP port must be between 1 and 65535.",
    )
    _max_email_size_not_negative = models.Constraint(
        "CHECK(max_email_size >= 0)",
        "The maximum email size cannot be negative. Leave it at 0 to fall back to "
        "the system-wide default.",
    )

    @api.depends("smtp_authentication")
    def _compute_smtp_authentication_info(self) -> None:
        info_by_type = {
            "login": _(
                "Connect to your server through your usual username and password. \n"
                "This is the most basic SMTP authentication process and "
                "may not be accepted by all providers. \n"
            ),
            "certificate": _(
                "Authenticate by using SSL certificates, belonging to your domain name. \n"
                "SSL certificates allow you to authenticate your mail server for the entire domain name."
            ),
            "cli": _(
                'Use the SMTP configuration set in the "Command Line Interface" arguments.'
            ),
        }
        for server in self:
            if info := info_by_type.get(server.smtp_authentication):
                server.smtp_authentication_info = info
            else:
                server.smtp_authentication_info = False

    @api.constrains(
        "smtp_authentication", "smtp_ssl_certificate", "smtp_ssl_private_key"
    )
    def _check_smtp_ssl_files(self) -> None:
        for mail_server in self:
            if mail_server.smtp_authentication != "certificate":
                continue
            if not mail_server.smtp_ssl_private_key:
                raise ValidationError(
                    _("SSL private key is missing for %s.", mail_server.name)
                )
            if not mail_server.smtp_ssl_certificate:
                raise ValidationError(
                    _("SSL certificate is missing for %s.", mail_server.name)
                )
            try:
                mail_server._read_certificate_material()
            except UserError as error:
                raise ValidationError(str(error)) from None

    @api.constrains("from_filter")
    def _check_from_filter(self) -> None:
        for mail_server in self:
            if junk := self._from_filter_index(mail_server.from_filter).unparsed:
                raise ValidationError(
                    _(
                        "%(entries)s is not a valid entry for the FROM filtering of "
                        "%(server)s. Give a comma-separated list of email addresses "
                        "(joe@example.com) or of domains (example.com).",
                        entries=", ".join(repr(part) for part in junk),
                        server=mail_server.display_name,
                    )
                )

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("write", servers=self.ids, fields=list(vals))
        if not vals.get("active", True):
            self._check_archivable()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_in_use(self) -> None:
        self._check_archivable(deleting=True)

    def _check_archivable(self, deleting: bool = False) -> None:
        usages_per_server = self._get_active_usages()
        servers = sorted(
            (server for server in self if usages_per_server.get(server.id)),
            key=lambda server: server.display_name,
        )
        if not servers:
            return
        _debug.logic(
            "archive_refused",
            servers=[server.id for server in servers],
            deleting=deleting,
            usages=sum(len(usages_per_server[server.id]) for server in servers),
        )

        is_multiple_server_usage = len(servers) > 1
        usage_details = []
        for server in servers:
            if is_multiple_server_usage:
                usage_details.append(
                    _(
                        "%s (Dedicated Outgoing Mail Server):",
                        server.display_name,
                    )
                )
            usage_details.extend(f"- {u}" for u in usages_per_server[server.id])

        details = {
            "server_usage": ", ".join(server.display_name for server in servers),
            "usage_details": "\n".join(usage_details),
        }
        if deleting and is_multiple_server_usage:
            message = _(
                "You cannot delete these Outgoing Mail Servers (%(server_usage)s) because they are still used in the following case(s):\n%(usage_details)s",
                **details,
            )
        elif deleting:
            message = _(
                "You cannot delete this Outgoing Mail Server (%(server_usage)s) because it is still used in the following case(s):\n%(usage_details)s",
                **details,
            )
        elif is_multiple_server_usage:
            message = _(
                "You cannot archive these Outgoing Mail Servers (%(server_usage)s) because they are still used in the following case(s):\n%(usage_details)s",
                **details,
            )
        else:
            message = _(
                "You cannot archive this Outgoing Mail Server (%(server_usage)s) because it is still used in the following case(s):\n%(usage_details)s",
                **details,
            )
        raise UserError(message)

    def _get_active_usages(self) -> dict[int, list[str]]:
        usages: dict[int, list[str]] = {}
        servers = self.with_context(active_test=False)
        for record in servers.filtered("mail_template_ids"):
            usages.setdefault(record.id, []).extend(
                _("%s (Email Template)", template.display_name)
                if template.active
                else _("%s (archived Email Template)", template.display_name)
                for template in record.mail_template_ids
            )
        return usages

    def _get_max_email_size(self, smtp_session: smtplib.SMTP | None = None) -> float:
        if len(self) > 1:
            raise ValueError(
                f"_get_max_email_size expects at most one server, got {self!r}"
            )
        configured = self.max_email_size or (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param_float("base.default_max_email_size", 10.0)
        )
        advertised = self._get_session_max_email_size(smtp_session)
        return min(configured, advertised) if advertised else configured

    @staticmethod
    def _get_session_max_email_size(smtp_session: smtplib.SMTP | None) -> float | None:
        size = (getattr(smtp_session, "esmtp_features", None) or {}).get("size")
        try:
            return float(size) / 1024**2 or None
        except TypeError, ValueError:
            return None

    def _from_filter_sender(self) -> str | None:
        self.check_singleton()
        return self._from_filter_index(self.from_filter).sender()

    def _from_filter_domain(self) -> str | None:
        self.check_singleton()
        return self._from_filter_index(self.from_filter).domain()

    def _get_test_email_from(self) -> str:
        self.check_singleton()
        email_from = self._from_filter_sender()
        if not email_from and (domain := self._from_filter_domain()):
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
            email_from = matching.default_from_email if matching else f"odoo@{domain}"
        if not email_from:
            email_from = self.env.user.email
        if not email_from or "@" not in email_from:
            raise UserError(
                _(
                    "Please configure an email on the current user to simulate "
                    "sending an email message via this outgoing server"
                )
            )
        return email_from

    def _get_test_email_to(self) -> str:
        return "noreply@odoo.com"

    @api.model
    def _get_outgoing_email_message(self, code: str) -> str:
        messages = {
            self.NO_VALID_RECIPIENT: _(
                "At least one valid recipient address should be specified for "
                "outgoing emails (To/Cc/Bcc)"
            ),
            self.NO_FOUND_FROM: _(
                "You must either provide a sender address explicitly or configure "
                "using the combination of `mail.catchall.domain` and "
                "`mail.default.from` ICPs, in the server configuration file or with "
                "the --email-from startup parameter."
            ),
            self.NO_FOUND_SMTP_FROM: _(
                "The Return-Path or From header is required for any outbound email"
            ),
            self.NO_VALID_FROM: _(
                "Malformed 'Return-Path' or 'From' address. It should contain one "
                "valid plain ASCII email"
            ),
        }
        return messages.get(code) or code

    def test_smtp_connection(self) -> dict[str, Any]:
        self._probe_smtp_connections()
        return self._get_connection_test_notification(_("Connection Test Successful!"))

    def action_update_max_email_size(self) -> dict[str, Any]:
        self.check_singleton()
        for server, advertised in self._probe_smtp_connections().items():
            if not advertised:
                raise UserError(
                    _(
                        'The server "%(server_name)s" doesn\'t return the maximum '
                        "email size.",
                        server_name=server.name,
                    )
                )
            server.max_email_size = advertised
        return self._get_connection_test_notification(
            _(
                "Email maximum size updated (%(details)s).",
                details=", ".join(
                    f"{server.name}: {human_size(server.max_email_size * 1024**2)}"
                    for server in self
                ),
            )
        )

    def _probe_smtp_connections(self) -> dict[Self, float | None]:
        self.check_access("write")
        if self._disable_send():
            _debug.logic("probe_refused", servers=self.ids, reason="send_disabled")
            raise UserError(
                _(
                    "Testing the SMTP connection is not possible because "
                    "outgoing emails are disabled (test mode or registry "
                    "initialization)."
                )
            )
        _debug.pipeline("probe_smtp_connections", servers=self.ids)
        return {server: server._probe_smtp_connection() for server in self}

    def _probe_smtp_connection(self) -> float | None:
        self.check_singleton()
        smtp = None
        in_data = False
        try:
            email_from = self._get_test_email_from()
            email_to = self._get_test_email_to()
            smtp = self._connect__(
                mail_server_id=self.id, allow_archived=True, smtp_from=email_from
            )
            code, repl = smtp.mail(email_from)
            if code != 250:
                raise UserError(
                    _(
                        "The server refused the sender address (%(email_from)s) with error %(repl)s",
                        email_from=email_from,
                        repl=repl,
                    )
                )
            code, repl = smtp.rcpt(email_to)
            if code not in (250, 251):
                raise UserError(
                    _(
                        "The server refused the test recipient (%(email_to)s) with error %(repl)s",
                        email_to=email_to,
                        repl=repl,
                    )
                )
            smtp.putcmd("data")
            in_data = True
            code, repl = smtp.getreply()
            if code != 354:
                raise UserError(
                    _(
                        "The server refused the test connection with error %(repl)s",
                        repl=repl,
                    )
                )
            _debug.logic("probe_accepted", server=self.id)
            return self._get_session_max_email_size(smtp)
        except UserError:
            raise
        except Exception as e:
            _debug.logic("probe_failed", server=self.id, error=type(e).__name__)
            raise self._prepare_connection_test_error(e, self) from e
        finally:
            if smtp is not None:
                if not in_data:
                    with suppress(Exception):
                        smtp.quit()
                with suppress(Exception):
                    smtp.close()

    @api.model
    def _get_connection_test_notification(self, message: str) -> dict[str, Any]:
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": message,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _prepare_connection_test_error(self, exc: Exception, server: Self) -> UserError:
        for exc_types, make_message in CONNECTION_TEST_ERRORS:
            if isinstance(exc, exc_types):
                return UserError(make_message(exc))

        _logger.warning(
            "Connection test on %s failed with a generic error.",
            server,
            exc_info=exc,
        )
        return UserError(
            _("Connection Test Failed! Here is what we got instead:\n %s", exc)
        )

    @classmethod
    def _disable_send(cls) -> bool:
        return modules.module.current_test or not cls.pool.ready

    def _connect__(
        self,
        smtp_from: str | None = None,
        mail_server_id: int | None = None,
        allow_archived: bool = False,
        resolve_server: bool = True,
    ) -> smtplib.SMTP | smtplib.SMTP_SSL | None:
        if self._disable_send():
            return None

        mail_server = None
        if mail_server_id:
            mail_server = self.sudo().browse(mail_server_id)
            mail_server._check_forced_mail_server(allow_archived, smtp_from)
        elif resolve_server:
            mail_server, smtp_from = self.sudo()._get_mail_server(smtp_from)
        if not mail_server:
            mail_server = self.env["ir.mail_server"]

        transport = mail_server._prepare_smtp_transport()
        _debug.logic(
            "connect",
            server=mail_server.id or None,
            forced=bool(mail_server_id),
            host=transport.server,
            port=transport.port,
            encryption=transport.encryption,
            smtp_from=smtp_from,
        )
        return self._open_smtp_connection(transport, smtp_from)

    def _prepare_smtp_transport(self) -> _SmtpTransport:
        if self and self.smtp_authentication != "cli":
            is_certificate = self.smtp_authentication == "certificate"
            encryption = self.smtp_encryption
            if is_certificate:
                ssl_context = self._prepare_ssl_context_from_certificate()
            elif encryption != "none":
                ssl_context = self._prepare_ssl_context_for_encryption(encryption)
            else:
                ssl_context = None
            return _SmtpTransport(
                server=self.smtp_host,
                port=self.smtp_port,
                user=None if is_certificate else self.smtp_user,
                password=None if is_certificate else self.smtp_pass,
                encryption=encryption,
                debug=self.smtp_debug,
                from_filter=self.from_filter,
                ssl_context=ssl_context,
                login_server=self,
                timeout=self._get_smtp_timeout(),
            )

        encryption = self._get_cli_encryption()
        cert_filename = tools.config.get("smtp_ssl_certificate_filename")
        key_filename = tools.config.get("smtp_ssl_private_key_filename")
        server = tools.config.get("smtp_server")
        if cert_filename and key_filename:
            if encryption is None:
                _logger.warning(
                    "An SMTP client certificate is configured (%s) but the "
                    "transport to %s is unencrypted, so it will not be "
                    "presented; enable --smtp-ssl or pick an encryption mode.",
                    cert_filename,
                    server,
                )
            ssl_context = self._prepare_ssl_context_from_cert_files(
                cert_filename, key_filename, encryption, server
            )
        elif encryption is not None:
            ssl_context = self._prepare_ssl_context_for_encryption(encryption)
        else:
            ssl_context = None

        return _SmtpTransport(
            server=server,
            port=tools.config.get("smtp_port", 25),
            user=tools.config.get("smtp_user"),
            password=tools.config.get("smtp_password"),
            encryption=encryption,
            debug=self.smtp_debug,
            from_filter=(
                self.from_filter
                if self
                else self.env["ir.mail_server"]._get_default_from_filter()
            ),
            ssl_context=ssl_context,
            login_server=self,
            timeout=self._get_smtp_timeout(),
        )

    @staticmethod
    def _get_cli_encryption() -> str | None:
        smtp_ssl = tools.config.get("smtp_ssl")
        if smtp_ssl is True:
            return "starttls_strict"
        return smtp_ssl or None

    @staticmethod
    def _get_smtp_timeout() -> float | None:
        return tools.config.get("smtp_timeout", SMTP_TIMEOUT) or None

    @staticmethod
    def _get_smtp_local_hostname() -> str | None:
        return tools.config.get("smtp_helo_name") or None

    @staticmethod
    def _encode_smtp_user(smtp_user: str) -> str:
        local, at, domain = smtp_user.rpartition("@")
        if not at or domain.isascii():
            return smtp_user
        try:
            return local + at + idna.encode(domain).decode("ascii")
        except idna.IDNAError:
            _logger.warning(
                "SMTP username %r has a non-ASCII part after the last @ that is not a "
                "valid IDN; authenticating with the literal value instead.",
                smtp_user,
            )
            return smtp_user

    def _open_smtp_connection(
        self, transport: _SmtpTransport, smtp_from: str | None
    ) -> smtplib.SMTP | smtplib.SMTP_SSL:
        if not transport.server:
            raise UserError(
                _(
                    "Missing SMTP Server\n"
                    "Please define at least one outgoing mail server, or set "
                    "--smtp-server in the command-line configuration.",
                )
            )

        with _debug.perf(
            "smtp_connect",
            host=transport.server,
            port=transport.port,
            encryption=transport.encryption,
            login=bool(transport.user),
        ):
            connection = self._open_smtp_socket(transport)

        self._stash_session_context(
            connection,
            _SmtpSessionContext(
                from_filter=transport.from_filter,
                smtp_from=smtp_from,
                mail_server_id=transport.login_server.id or None,
            ),
        )
        return connection

    @api.model
    def _open_smtp_socket(
        self, transport: _SmtpTransport
    ) -> smtplib.SMTP | smtplib.SMTP_SSL:
        local_hostname = self._get_smtp_local_hostname()
        if transport.encryption in IMPLICIT_TLS_ENCRYPTIONS:
            connection = smtplib.SMTP_SSL(
                transport.server,
                transport.port,
                local_hostname=local_hostname,
                timeout=transport.timeout,
                context=transport.ssl_context,
            )
        else:
            connection = smtplib.SMTP(
                transport.server,
                transport.port,
                local_hostname=local_hostname,
                timeout=transport.timeout,
            )
        try:
            if transport.debug:
                connection._print_debug = _log_smtp_debug
            connection.set_debuglevel(transport.debug)
            if transport.encryption in STARTTLS_ENCRYPTIONS:
                connection.starttls(context=transport.ssl_context)

            if transport.user:
                transport.login_server._smtp_login__(
                    connection,
                    self._encode_smtp_user(transport.user),
                    transport.password or "",
                )

            connection.ehlo_or_helo_if_needed()
        except Exception:
            connection.close()
            raise
        return connection

    @staticmethod
    def _stash_session_context(
        connection: smtplib.SMTP, context: _SmtpSessionContext
    ) -> None:
        _SESSION_CONTEXTS[connection] = context

    @staticmethod
    def _is_smtputf8_supported(smtp_session: smtplib.SMTP | None) -> bool:
        features = getattr(smtp_session, "esmtp_features", None)
        if features is None:
            return True
        return "smtputf8" in features

    @staticmethod
    def _read_session_context(
        smtp_session: smtplib.SMTP | None,
    ) -> _SmtpSessionContext:
        if smtp_session is None:
            return _SmtpSessionContext()
        try:
            return _SESSION_CONTEXTS[smtp_session]
        except KeyError, TypeError:
            _logger.warning(
                "Sending through an SMTP session this model did not open (%r); no "
                "from_filter can be enforced on it.",
                smtp_session,
            )
            return _SmtpSessionContext()

    @staticmethod
    def _prepare_ssl_load_error(exc: Exception) -> UserError:
        if isinstance(exc, (SSLCryptoError, ssl.SSLError, ValueError)):
            return UserError(
                _(
                    "The private key or the certificate is not a valid file. \n%s",
                    str(exc),
                )
            )
        return UserError(
            _("Could not load your certificate / private key. \n%s", str(exc))
        )

    @staticmethod
    def _prepare_client_ssl_context(
        encryption: str | None, smtp_server: str | None
    ) -> PyOpenSSLContext:
        ssl_context = PyOpenSSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if encryption in VERIFIED_ENCRYPTIONS:
            ssl_context.set_default_verify_paths()
            ssl_context._ctx.set_verify(
                VERIFY_PEER | VERIFY_FAIL_IF_NO_PEER_CERT,
                functools.partial(
                    _check_hostname_callback,
                    hostname=smtp_server,
                ),
            )
        else:
            ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    def _read_certificate_material(self) -> tuple[list[Any], Any]:
        self.check_singleton()
        try:
            chain = load_pem_x509_certificates(
                base64.b64decode(self.smtp_ssl_certificate)
            )
            private_key = load_pem_private_key(
                base64.b64decode(self.smtp_ssl_private_key), password=None
            )
        except CERTIFICATE_LOAD_ERRORS as e:
            raise self._prepare_ssl_load_error(e) from None
        if chain[0].public_key() != private_key.public_key():
            raise UserError(
                _(
                    "The SSL certificate of %s does not match its private key.",
                    self.display_name,
                )
            )
        return chain, private_key

    def _prepare_ssl_context_from_certificate(self) -> PyOpenSSLContext:
        self.check_singleton()
        ssl_context = self._prepare_client_ssl_context(
            self.smtp_encryption, self.smtp_host
        )
        (leaf, *intermediates), private_key = self._read_certificate_material()
        try:
            ssl_context._ctx.use_certificate(leaf)
            for intermediate in intermediates:
                ssl_context._ctx.add_extra_chain_cert(intermediate)
            ssl_context._ctx.use_privatekey(private_key)
        except CERTIFICATE_LOAD_ERRORS as e:
            raise self._prepare_ssl_load_error(e) from None
        return ssl_context

    def _prepare_ssl_context_from_cert_files(
        self,
        cert_filename: str,
        key_filename: str,
        encryption: str | None = None,
        smtp_server: str | None = None,
    ) -> PyOpenSSLContext:
        ssl_context = self._prepare_client_ssl_context(encryption, smtp_server)
        try:
            ssl_context.load_cert_chain(cert_filename, keyfile=key_filename)
            ssl_context._ctx.check_privatekey()
        except CERTIFICATE_LOAD_ERRORS as e:
            raise self._prepare_ssl_load_error(e) from None
        return ssl_context

    @staticmethod
    def _prepare_ssl_context_for_encryption(encryption: str) -> ssl.SSLContext:
        ssl_context = ssl.create_default_context()
        if encryption in VERIFIED_ENCRYPTIONS:
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED
        else:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    def _check_forced_mail_server(
        self, allow_archived: bool, smtp_from: str | None
    ) -> None:
        if not allow_archived and not self.active:
            _debug.logic("forced_server_archived", server=self.id)
            raise UserError(
                _(
                    'The server "%s" cannot be used because it is archived.',
                    self.display_name,
                )
            )
        if not self.owner_user_id:
            return
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

    def _check_session_mail_server(
        self, smtp_session: smtplib.SMTP, mail_server_id: int | None
    ) -> None:
        if not mail_server_id:
            return
        session_server_id = self._read_session_context(smtp_session).mail_server_id
        if session_server_id != mail_server_id:
            _debug.logic(
                "session_server_mismatch",
                session_server=session_server_id,
                forced_server=mail_server_id,
            )
            e = (
                f"smtp_session was opened for mail server {session_server_id}, "
                f"not {mail_server_id}; connect through the forced server instead"
            )
            raise ValueError(e)

    def _smtp_login__(
        self, connection: smtplib.SMTP, smtp_user: str, smtp_password: str
    ) -> None:
        connection.login(smtp_user, smtp_password)

    def _prepare_email__(
        self,
        email_from: str | None,
        email_to: str | list[str],
        subject: str,
        body: str,
        email_cc: list[str] | None = None,
        email_bcc: list[str] | None = None,
        reply_to: str | bool = False,
        attachments: list[tuple[str, bytes, str]] | None = None,
        message_id: str | None = None,
        references: str | None = None,
        object_id: str | bool = False,
        subtype: str = "plain",
        headers: dict[str, str] | None = None,
        body_alternative: str | None = None,
        subtype_alternative: str = "plain",
    ) -> EmailMessage:
        email_from = (
            email_from
            or self.env.context.get("domain_notifications_email")
            or self._get_default_from_address()
        )
        if not email_from:
            raise OutgoingEmailError(
                self._get_outgoing_email_message(self.NO_FOUND_FROM), self.NO_FOUND_FROM
            )

        headers = headers or {}
        email_cc = email_cc or []
        email_bcc = email_bcc or []

        msg = EmailMessage(policy=email.policy.SMTP)
        if not message_id:
            if object_id:
                message_id = tools.mail.generate_tracking_message_id(object_id)
            else:
                message_id = make_msgid()
        msg["Message-Id"] = message_id
        if references:
            msg["references"] = references
        msg["Subject"] = subject
        msg["From"] = email_from
        msg["Reply-To"] = reply_to or email_from
        if email_to:
            msg["To"] = email_to
        if email_cc:
            msg["Cc"] = email_cc
        if email_bcc:
            msg["Bcc"] = email_bcc
        msg["Date"] = datetime.datetime.now(datetime.UTC)
        for key, value in headers.items():
            del msg[key]
            if not value:
                continue
            msg[key] = value

        self._update_email_body(
            msg, body or "", subtype, body_alternative, subtype_alternative
        )
        self._add_email_attachments(msg, attachments or ())
        return msg

    @api.model
    def _update_email_body(
        self,
        msg: EmailMessage,
        body: str,
        subtype: str,
        body_alternative: str | None,
        subtype_alternative: str,
    ) -> None:
        if body_alternative:
            alternative, alternative_subtype = body_alternative, subtype_alternative
        elif subtype == "html":
            alternative, alternative_subtype = tools.html2plaintext(body), "plain"
        else:
            msg.set_content(body, subtype=subtype, charset="utf-8")
            return
        msg["MIME-Version"] = "1.0"
        msg.add_alternative(alternative, subtype=alternative_subtype, charset="utf-8")
        msg.add_alternative(body, subtype=subtype, charset="utf-8")

    @api.model
    def _add_email_attachments(
        self, msg: EmailMessage, attachments: Iterable[tuple[str, bytes, str]]
    ) -> None:
        for fname, fcontent, mime in attachments:
            maintype, att_subtype = (
                mime.split("/", 1)
                if mime and "/" in mime
                else ("application", "octet-stream")
            )
            if (maintype, att_subtype) == ("message", "rfc822"):
                msg.add_attachment(BytesParser().parsebytes(fcontent), filename=fname)
            else:
                msg.add_attachment(fcontent, maintype, att_subtype, filename=fname)

    @api.model
    def _get_default_bounce_address(self) -> str | None:
        if bounce := self.env.company.bounce_email:
            _debug.logic("bounce_address", by="company", company=self.env.company.id)
            return bounce
        return tools.config.get("email_from")

    @api.model
    def _get_default_from_address(self) -> str | None:
        if default_from := self.env.company.default_from_email:
            _debug.logic("from_address", by="company", company=self.env.company.id)
            return default_from
        return tools.config.get("email_from")

    @api.model
    def _get_notifications_email(self) -> str | bool:
        return email_normalize(
            self.env.context.get("domain_notifications_email")
            or self._get_default_from_address()
        )

    @api.model
    def _get_default_from_filter(self) -> str | None:
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail.default.from_filter", tools.config.get("from_filter"))
        )

    def _prepare_email_message__(
        self, message: EmailMessage, smtp_session: smtplib.SMTP
    ) -> tuple[str, list[str], EmailMessage]:
        bounce_address = (
            self.env.context.get("domain_bounce_address")
            or message["Return-Path"]
            or self._get_default_bounce_address()
            or message["From"]
        )

        smtp_from = message["From"] or bounce_address
        if not smtp_from:
            raise OutgoingEmailError(
                self._get_outgoing_email_message(self.NO_FOUND_SMTP_FROM),
                self.NO_FOUND_SMTP_FROM,
            )

        smtp_to_list = self._prepare_smtp_to_list(message, smtp_session)
        if not smtp_to_list:
            raise OutgoingEmailError(
                self._get_outgoing_email_message(self.NO_VALID_RECIPIENT),
                self.NO_VALID_RECIPIENT,
            )

        session_context = self._read_session_context(smtp_session)
        from_filter = session_context.from_filter
        smtp_from = session_context.smtp_from or smtp_from
        notifications_email = self._get_notifications_email()
        if (
            notifications_email
            and email_normalize(smtp_from) == notifications_email
            and email_normalize(message["From"]) != notifications_email
        ):
            smtp_from = encapsulate_email(message["From"], notifications_email)

        message = self._copy_message_detached(message)
        self._alter_message__(message, smtp_from)

        if self._match_from_filter(bounce_address, from_filter):
            _debug.logic("envelope_from_bounce", bounce=bounce_address)
            smtp_from = bounce_address

        envelope_sender = self._get_envelope_sender(smtp_from)
        if not envelope_sender:
            raise OutgoingEmailError(
                _(
                    "Malformed 'Return-Path' or 'From' address: %s - It should "
                    "contain one valid plain ASCII email",
                    smtp_from,
                ),
                self.NO_VALID_FROM,
            )
        smtp_from = envelope_sender

        if not self._is_smtputf8_supported(smtp_session):
            self._check_ascii_envelope(smtp_from, smtp_to_list)

        return smtp_from, smtp_to_list, message

    @api.model
    def _get_envelope_sender(self, address: str) -> str | None:
        parsed = getaddresses([address])
        if parsed and (angle_addr := parsed[0][1]):
            extracted = extract_rfc2822_addresses(angle_addr)
            if extracted:
                return extracted[0]
        extracted = extract_rfc2822_addresses(address)
        return extracted[-1] if extracted else None

    @api.model
    def _check_ascii_envelope(self, smtp_from: str, smtp_to_list: list[str]) -> None:
        if not smtp_from.isascii():
            _debug.logic("envelope_not_ascii", part="from")
            raise OutgoingEmailError(
                _(
                    "Malformed 'Return-Path' or 'From' address: %s - It should "
                    "contain one valid plain ASCII email (this server does not "
                    "support SMTPUTF8)",
                    smtp_from,
                ),
                self.NO_VALID_FROM,
            )
        if non_ascii := [address for address in smtp_to_list if not address.isascii()]:
            _debug.logic("envelope_not_ascii", part="to", count=len(non_ascii))
            raise OutgoingEmailError(
                _(
                    "Recipient address requires SMTPUTF8, which this server does "
                    "not support: %s",
                    ", ".join(non_ascii),
                ),
                self.NO_VALID_RECIPIENT,
            )

    @staticmethod
    def _copy_message_detached(message: EmailMessage) -> EmailMessage:
        detached = copy.copy(message)
        detached._headers = list(message._headers)
        if isinstance(message._payload, list):
            detached._payload = list(message._payload)
        return detached

    @api.model
    def _alter_message__(self, message: EmailMessage, smtp_from: str) -> None:
        if x_forge_to := message["X-Forge-To"]:
            del message["To"]
            message["To"] = x_forge_to
        elif x_msg_add_to := message["X-Msg-To-Add"]:
            to = message["To"] or ""
            seen = set(tools.mail.email_normalize_all(to))
            additions = []
            for address in tools.mail.email_split_and_format(x_msg_add_to):
                normalized = tools.mail.email_normalize(address, strict=False)
                if normalized and normalized in seen:
                    continue
                if normalized:
                    seen.add(normalized)
                additions.append(address)
            del message["To"]
            if new_to := ", ".join(part for part in [str(to), *additions] if part):
                message["To"] = new_to

        if message["From"] != smtp_from:
            del message["From"]
            message["From"] = smtp_from

        del message["Bcc"]
        del message["Return-Path"]
        del message["X-Forge-To"]
        del message["X-Msg-To-Add"]

    @api.model
    def _prepare_smtp_to_list(
        self, message: EmailMessage, smtp_session: smtplib.SMTP
    ) -> list[str]:
        validated_to = set(self.env.context.get("send_validated_to") or ())
        skip_to = set(self.env.context.get("send_smtp_skip_to") or ())

        smtp_to_list = []
        seen = set()
        for header in (message["To"], message["Cc"], message["Bcc"]):
            for address in extract_rfc2822_addresses(header):
                if not address:
                    continue
                normalized = email_normalize(address, strict=False)
                dedup_key = normalized or address.lower()
                if dedup_key in seen or normalized in skip_to:
                    continue
                if validated_to and not validated_to & {address, normalized}:
                    continue
                seen.add(dedup_key)
                smtp_to_list.append(address)
        return smtp_to_list

    @api.private
    @api.model
    def send_email(
        self,
        message: EmailMessage,
        mail_server_id: int | None = None,
        smtp_session: smtplib.SMTP | None = None,
    ) -> str:
        smtp = smtp_session
        owns_connection = not smtp_session
        if smtp:
            self._check_session_mail_server(smtp, mail_server_id)
        else:
            smtp = self._connect__(
                smtp_from=message["From"], mail_server_id=mail_server_id
            )

        try:
            smtp_from, smtp_to_list, message = self._prepare_email_message__(
                message, smtp
            )

            if self._disable_send():
                _test_logger.debug("skip sending email in test mode")
                _debug.logic("send_skipped_test_mode", message_id=message["Message-Id"])
                return message["Message-Id"]

            message_id = message["Message-Id"]
            try:
                with _debug.perf(
                    "smtp_send",
                    message_id=message_id,
                    smtp_from=smtp_from,
                    recipients=len(smtp_to_list),
                    owns_connection=owns_connection,
                ):
                    smtp.send_message(message, smtp_from, smtp_to_list)
            except smtplib.SMTPServerDisconnected:
                raise
            except Exception as e:
                msg = _(
                    "Mail delivery failed via SMTP server '%(server)s'.\n%(exception_name)s: %(message)s",
                    server=getattr(smtp, "_host", None) or "unknown",
                    exception_name=e.__class__.__name__,
                    message=e,
                )
                _logger.warning(msg, exc_info=True)
                raise MailDeliveryError(_("Mail Delivery Failed"), msg) from e
            return message_id
        finally:
            if owns_connection and smtp is not None:
                try:
                    smtp.quit()
                except Exception:
                    with suppress(Exception):
                        smtp.close()

    def _get_domain_mail_servers_allowed(self) -> fields.Domain:
        return fields.Domain("owner_user_id", "=", False)

    def _get_mail_server(
        self, email_from: str | None, mail_servers: Self | None = None
    ) -> tuple[Self | None, str | None]:
        notifications_email = self._get_notifications_email()

        if mail_servers is None:
            mail_servers = self.sudo().search(self._get_domain_mail_servers_allowed())
        mail_servers = mail_servers.filtered("active")
        index = self._from_filter_memo()

        if email_normalize(email_from) and (
            mail_server := self._get_first_server_for_email(
                mail_servers, index, email_from
            )
        ):
            _debug.logic("mail_server", server=mail_server.id, by="from_filter")
            return mail_server, email_from

        fallbacks = self._filtered_mail_servers_fallback(mail_servers)

        if notifications_email and (
            mail_server := self._get_first_server_for_email(
                fallbacks, index, notifications_email
            )
        ):
            _debug.logic("mail_server", server=mail_server.id, by="notifications_email")
            return mail_server, notifications_email

        preferred = notifications_email or email_from
        if mail_server := next(
            (server for server in fallbacks if index(server).unrestricted), None
        ):
            _debug.logic("mail_server", server=mail_server.id, by="unrestricted")
            return mail_server, preferred

        if fallbacks:
            _logger.warning(
                "No mail server matches the from_filter, using %s as fallback",
                preferred,
            )
            _debug.logic("mail_server", server=fallbacks[0].id, by="first_fallback")
            return fallbacks[0], preferred

        _debug.logic("mail_server", server=None, by="cli")
        return None, self._get_cli_envelope_sender(email_from, notifications_email)

    @api.model
    def _from_filter_memo(self) -> Callable[[Self], _FromFilter]:
        indexes: dict[int, _FromFilter] = {}

        def index(mail_server: Self) -> _FromFilter:
            entry = indexes.get(mail_server.id)
            if entry is None:
                entry = indexes[mail_server.id] = self._from_filter_index(
                    mail_server.from_filter
                )
            return entry

        return index

    @api.model
    def _get_first_server_for_email(
        self,
        candidates: Self,
        index: Callable[[Self], _FromFilter],
        email_from: str,
    ) -> Self | None:
        normalized = email_normalize(email_from)
        domain = email_domain_extract(normalized)
        return next(
            (s for s in candidates if normalized in index(s).emails), None
        ) or next((s for s in candidates if domain in index(s).domains), None)

    @api.model
    def _get_cli_envelope_sender(
        self, email_from: str | None, notifications_email: str | bool
    ) -> str | None:
        from_filter = self.env["ir.mail_server"]._get_default_from_filter()

        if self._match_from_filter(email_from, from_filter):
            return email_from

        if notifications_email and self._match_from_filter(
            notifications_email, from_filter
        ):
            return notifications_email

        _logger.warning(
            "The from filter of the CLI configuration does not match the notification email "
            "or the user email, using %s as fallback",
            notifications_email or email_from,
        )
        return notifications_email or email_from

    @api.model
    def _filtered_mail_servers_fallback(self, servers: Self) -> Self:
        return servers.filtered(lambda s: not s.owner_user_id)

    @api.model
    def _match_from_filter(
        self, email_from: str | None, from_filter: str | None
    ) -> bool:
        return self._from_filter_index(from_filter).matches(email_from)

    @api.model
    def _from_filter_index(self, from_filter: str | None) -> _FromFilter:
        emails: dict[str, None] = {}
        domains: dict[str, None] = {}
        unparsed: dict[str, None] = {}
        for part in self._parse_from_filter(from_filter):
            if "@" in part:
                normalized = email_normalize(part)
                local, _at, domain = (normalized or "").rpartition("@")
                if normalized and local and DOMAIN_PATTERN.match(domain):
                    emails[normalized] = None
                else:
                    unparsed[part] = None
            elif (normalized := email_domain_normalize(part)) and DOMAIN_PATTERN.match(
                normalized
            ):
                domains[normalized] = None
            else:
                unparsed[part] = None
        return _FromFilter(tuple(emails), tuple(domains), tuple(unparsed))

    @api.model
    def _parse_from_filter(self, from_filter: str | None) -> list[str]:
        return [part.strip() for part in (from_filter or "").split(",") if part.strip()]

    def _get_personal_mail_servers_limit(self) -> int:
        return self.env["ir.config_parameter"]._get_positive_int_param(
            "mail.server.personal.limit.minutes", 30
        )

    def _get_personal_mail_server_grace(self) -> int:
        return self.env["ir.config_parameter"]._get_positive_int_param(
            "mail.server.personal.setup.grace.minutes", 1440
        )

    @api.onchange("smtp_encryption")
    def _onchange_smtp_encryption(self) -> None:
        if self.smtp_encryption in IMPLICIT_TLS_ENCRYPTIONS:
            if self.smtp_port == 25:
                self.smtp_port = 465
        elif self.smtp_port == 465:
            self.smtp_port = 25
