import typing

from odoo import fields, models

if typing.TYPE_CHECKING:
    from .mail_alias_domain import MailAliasDomain


class MailConfig(models.Model):
    _name = "mail.config"
    _description = "A company's mail configuration"
    _inherit = ["mixin.company.config"]

    alias_domain_id: MailAliasDomain = fields.Many2one(
        comodel_name="mail.alias.domain",
        string="Email Domain",
        default=lambda self: self._default_alias_domain_id(),
        index="btree_not_null",
    )
    email_primary_color = fields.Char(
        string="Email Button Text",
        default="#FFFFFF",
    )
    email_secondary_color = fields.Char(
        string="Email Button Color",
        default="#875A7B",
    )

    def _default_alias_domain_id(self) -> MailAliasDomain:
        return self.env["mail.alias.domain"]._get_default_domain()
