import typing

from odoo import api, fields, models, tools

if typing.TYPE_CHECKING:
    from .mail_alias_domain import MailAliasDomain


class ResCompany(models.Model):
    _inherit = "res.company"

    mail_config_id = fields.Many2one(
        comodel_name="mail.config",
        compute="_compute_mail_config_id",
        search="_search_mail_config_id",
    )
    alias_domain_id: MailAliasDomain = fields.Many2one(
        related="mail_config_id.alias_domain_id",
        readonly=False,
    )
    bounce_email = fields.Char(compute="_compute_bounce")
    bounce_formatted = fields.Char(
        string="Bounce",
        compute="_compute_bounce",
    )
    catchall_email = fields.Char(compute="_compute_catchall")
    catchall_formatted = fields.Char(
        string="Catchall",
        compute="_compute_catchall",
    )
    default_from_email = fields.Char(
        related="alias_domain_id.default_from_email",
        string="Default From",
        readonly=True,
    )
    email_formatted = fields.Char(
        string="Formatted Email",
        compute="_compute_email_formatted",
        compute_sudo=True,
    )
    email_primary_color = fields.Char(
        related="mail_config_id.email_primary_color",
        readonly=False,
    )
    email_secondary_color = fields.Char(
        related="mail_config_id.email_secondary_color",
        readonly=False,
    )

    def _search_mail_config_id(self, operator, value):
        return self._search_config_link("mail.config", operator, value)

    def _compute_mail_config_id(self):
        configs = self.env["mail.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.mail_config_id = by_company.get(company.id, False)

    @api.depends("alias_domain_id.bounce_email", "name")
    def _compute_bounce(self) -> None:
        self.bounce_email = ""
        self.bounce_formatted = ""

        for company in self.filtered("alias_domain_id"):
            bounce_email = company.alias_domain_id.bounce_email
            company.bounce_email = bounce_email
            company.bounce_formatted = bounce_email and tools.formataddr(
                (company.name, bounce_email)
            )

    @api.depends("alias_domain_id.catchall_email", "name")
    def _compute_catchall(self) -> None:
        self.catchall_email = ""
        self.catchall_formatted = ""

        for company in self.filtered("alias_domain_id"):
            catchall_email = company.alias_domain_id.catchall_email
            company.catchall_email = catchall_email
            company.catchall_formatted = catchall_email and tools.formataddr(
                (company.name, catchall_email)
            )

    @api.depends("partner_id", "catchall_formatted")
    def _compute_email_formatted(self) -> None:
        for company in self:
            if company.partner_id.email_formatted:
                company.email_formatted = company.partner_id.email_formatted
            elif company.catchall_formatted:
                company.email_formatted = company.catchall_formatted
            else:
                company.email_formatted = ""
