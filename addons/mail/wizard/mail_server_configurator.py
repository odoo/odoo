# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, tools, models
from odoo.exceptions import UserError
from odoo.tools.mail import email_domain_extract, email_normalize


class MailServerConfigurator(models.TransientModel):
    _name = "mail.server.configurator"
    _description = "Mail Server Configurator"

    SMTP_HOSTS = {
        "gmail_oauth": "smtp.gmail.com",
        "outlook_oauth": "smtp-mail.outlook.com",
        "gmx": "mail.gmx.com",
        "mailjet": "in-v3.mailjet.com",
    }

    IMAP_HOSTS = {
        "gmail_oauth": "imap.gmail.com",
        "outlook_oauth": "outlook.office365.com",
        "gmx": "imap.gmx.com",
    }

    server_type = fields.Selection(
        selection=[
            ("gmail_oauth", "Gmail"),
            ("outlook_oauth", "Outlook"),
            ("gmx", "GMX"),
            ("mailjet", "Mailjet"),
        ],
        string="Server Type",
        default="gmail_oauth",
        required=True,
    )
    email = fields.Char("Email Address", required=True)
    login = fields.Char("Login", help="Login if the login is different from the email")
    password = fields.Char("Application Password")
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company)
    catchall_domain = fields.Char(
        "Catchall Domain", compute="_compute_catchall_domain",
        readonly=False, store=True)
    is_only_outgoing = fields.Boolean(
        "Only Outgoing",
        help="Do not configure the incoming mail server")
    is_default = fields.Boolean(
        "Use by Default",
        help="This mail server will be used by default for the company you selected (and will be used to send most of the notifications, etc)")
    need_module_install = fields.Boolean("Need Module Install", compute="_compute_need_module_install")
    is_default_warning = fields.Char("Default Warning", compute="_compute_is_default_warning")
    is_imap_supported = fields.Boolean("Is IMAP supported", compute="_compute_is_imap_supported")
    is_login_editable = fields.Boolean("Is Login Editable", compute="_compute_is_login_editable")
    is_password_required = fields.Boolean("Need Password", compute="_compute_is_password_required")

    @api.depends("company_id")
    def _compute_catchall_domain(self):
        for link in self:
            link.catchall_domain = link.company_id.alias_domain_id.name

    @api.depends("server_type")
    def _compute_is_password_required(self):
        for link in self:
            link.is_password_required = link.server_type in ("gmx", "mailjet")

    @api.depends("server_type")
    def _compute_need_module_install(self):
        for link in self:
            module = link._get_module()
            link.need_module_install = module and module.state != "installed"

    @api.depends("is_default", "email", "catchall_domain")
    def _compute_is_default_warning(self):
        for link in self:
            default_alias = link.company_id.alias_domain_id
            if not default_alias or not link.is_default:
                link.is_default_warning = False
                continue

            is_default_warning = []
            if link.email != default_alias.default_from_email:
                is_default_warning.append(_(
                    "The current default email is %(current)s and it will be overwritten with %(new)s.",
                    current=default_alias.default_from_email,
                    new=link.email,
                ))
            if link.catchall_domain != default_alias.name:
                new_catchall_email = f"{default_alias.catchall_alias}@{link.catchall_domain}"
                is_default_warning.append(_(
                    "The current catchall email is %(current)s and it will be overwritten with %(new)s.",
                    current=default_alias.catchall_email,
                    new=new_catchall_email,
                ))

            if is_default_warning and len(default_alias.company_ids) > 1:
                is_default_warning.append(_(
                    "This configuration is also used by %s.",
                    ", ".join((default_alias.company_ids - self.company_id).mapped("name"))
                ))

            link.is_default_warning = "\n".join(is_default_warning) if is_default_warning else False

    @api.depends("server_type")
    def _compute_is_imap_supported(self):
        for link in self:
            link.is_imap_supported = link.server_type != "mailjet"

    @api.depends("server_type")
    def _compute_is_login_editable(self):
        for link in self:
            link.is_login_editable = link.server_type == "mailjet"

    @api.onchange("server_type")
    def _onchange_server_type(self):
        if not self.is_login_editable:
            self.login = False
        if not self.is_imap_supported:
            self.is_only_outgoing = False

    def action_install(self):
        """"Install the module if needed and re-open the wizard."""
        module = self._get_module()
        if module and module.state != "installed":
            module.button_immediate_install()

        return {  # keep the wizard opened
            "name": _("Configure a Server"),
            "type": "ir.actions.act_window",
            "res_model": "mail.server.configurator",
            "target": "new",
            "res_id": self.id,
            "views": [[False, "form"]],
        }

    def action_setup(self):
        """Configure the outgoing / incoming mail servers."""
        self.ensure_one()

        if not self.email or not email_normalize(self.email):
            raise UserError(_("Invalid email: %s", self.email))

        module = self._get_module()
        if module and module.state != "installed":
            raise UserError(_("Please install %s first.", module.name))

        values = self._prepare_ir_mail_server_values()
        values["smtp_authentication"] = "login"
        values["smtp_host"] = self.SMTP_HOSTS[self.server_type]

        smtp_server = self._create_ir_mail_server(values)
        smtp_server.test_smtp_connection()

        if self.is_only_outgoing:
            return {
                "type": "ir.actions.act_window",
                "res_model": "ir.mail_server",
                "res_id": smtp_server.id,
                "view_ids": [(False, "form")],
                "view_mode": "form",
            }

        # configure incoming mail server
        values = self._prepare_fetchmail_server_values()
        values["server"] = self.IMAP_HOSTS[self.server_type]
        imap_server = self.env["fetchmail.server"].create(values)
        imap_server.button_confirm_login()
        return {
            "type": "ir.actions.act_window",
            "res_model": "fetchmail.server",
            "res_id": imap_server.id,
            "view_ids": [(False, "form")],
            "view_mode": "form",
        }

    def _get_module(self):
        """Return the <ir.module.module> related to the server type."""
        modules = {
            "gmail_oauth": "google_gmail",
            "outlook_oauth": "microsoft_outlook",
        }
        module_name = modules.get(self.server_type)
        if not module_name:
            return

        if module := self.env["ir.module.module"].search([("name", "=", module_name)], limit=1):
            return module
        raise UserError(_("The module %s is needed.", module_name))

    def _prepare_ir_mail_server_values(self):
        self.ensure_one()

        normalized_email = tools.email_normalize(self.email)
        if not normalized_email:
            raise UserError(_("Wrong email address %s.", self.email))

        login = self.login if self.is_login_editable and self.login else normalized_email
        return {
            "name": self.email,
            "smtp_user": login,
            "smtp_pass": self.is_password_required and self.password,
            "from_filter": normalized_email,
            "smtp_port": 587,
            "smtp_encryption": "starttls",
        }

    def _prepare_fetchmail_server_values(self):
        self.ensure_one()

        normalized_email = tools.email_normalize(self.email)
        if not normalized_email:
            raise UserError(_("Wrong email address %s.", self.email))

        return {
            "name": self.email,
            "is_ssl": True,
            "password": self.password,
            "port": 993,
            "server_type": "imap",
            "user": normalized_email,
        }

    def _create_ir_mail_server(self, values):
        """Create the ir.mail_server and make it default if needed."""
        self.ensure_one()

        smtp_server = self.env["ir.mail_server"].create(values)

        # configure the mail.alias.domain
        if self.is_default:
            alias_domain = self.company_id.alias_domain_id
            if alias_domain:
                alias_domain.name = self.catchall_domain
                alias_domain.default_from = self.email
            else:
                self.company_id.alias_domain_id = self.env["mail.alias.domain"].create({
                    "name": self.catchall_domain or email_domain_extract(self.email),
                    "default_from": self.email,
                })
        return smtp_server
