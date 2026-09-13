import typing

from odoo import api, fields, models, tools

if typing.TYPE_CHECKING:
    from .mail_alias_domain import MailAliasDomain


class ResCompany(models.Model):
    _inherit = "res.company"

    alias_domain_id: MailAliasDomain = fields.Many2one(
        comodel_name="mail.alias.domain",
        string="Email Domain",
        default=lambda self: self._default_alias_domain_id(),
        index="btree_not_null",
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
        string="Email Button Text",
        default="#FFFFFF",
        readonly=False,
    )
    email_secondary_color = fields.Char(
        string="Email Button Color",
        default="#875A7B",
        readonly=False,
    )

    def _default_alias_domain_id(self) -> MailAliasDomain:
        return self.env["mail.alias.domain"]._get_default_domain()

    @api.depends("alias_domain_id.bounce_email", "name")
    def _compute_bounce(self) -> None:
        self.bounce_email = ""
        self.bounce_formatted = ""

        for company in self.filtered("alias_domain_id"):
            bounce_email = company.alias_domain_id.bounce_email
            company.bounce_email = bounce_email
            company.bounce_formatted = tools.formataddr((company.name, bounce_email))

    @api.depends("alias_domain_id.catchall_email", "name")
    def _compute_catchall(self) -> None:
        self.catchall_email = ""
        self.catchall_formatted = ""

        for company in self.filtered("alias_domain_id"):
            catchall_email = company.alias_domain_id.catchall_email
            company.catchall_email = catchall_email
            company.catchall_formatted = tools.formataddr(
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
