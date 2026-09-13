import logging

from odoo import api, fields, models
from odoo.tools import email_normalize

_logger = logging.getLogger(__name__)


class MailGroupMember(models.Model):
    _name = "mail.group.member"
    _description = "Mailing List Member"
    _rec_name = "email"

    email = fields.Char(
        compute="_compute_email",
        store=True,
        readonly=False,
    )
    email_normalized = fields.Char(
        string="Normalized Email",
        compute="_compute_email_normalized",
        store=True,
        index=True,
    )
    mail_group_id = fields.Many2one(
        comodel_name="mail.group",
        string="Group",
        index=True,
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        ondelete="cascade",
    )

    _unique_partner = models.UniqueIndex(
        "(partner_id, mail_group_id) WHERE partner_id IS NOT NULL",
        "This partner is already subscribed to the group",
    )

    @api.depends("partner_id.email")
    def _compute_email(self):
        for member in self:
            if member.partner_id:
                member.email = member.partner_id.email
            elif not member.email:
                member.email = False

    @api.depends("email")
    def _compute_email_normalized(self):
        for moderation in self:
            moderation.email_normalized = email_normalize(moderation.email)
