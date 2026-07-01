# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models
from odoo.tools import html2plaintext
from odoo.exceptions import ValidationError


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    lead_ids = fields.One2many(
        "crm.lead",
        "origin_channel_id",
        string="Leads",
        groups="sales_team.group_sale_salesman",
        help="The channel becomes accessible to sales users when leads are set.",
    )
    has_crm_lead = fields.Boolean(compute="_compute_has_crm_lead", store=True)
    _has_crm_lead_index = models.Index("(has_crm_lead) WHERE has_crm_lead IS TRUE")

    @api.depends("lead_ids")
    def _compute_has_crm_lead(self):
        for channel in self:
            channel.has_crm_lead = bool(channel.lead_ids)

    def execute_command_lead(self, **kwargs):
        if self.channel_type not in self._types_allowing_create_lead():
            raise ValidationError(
                self.env._(
                    "Lead creation is not supported on channel type %(channel_type)s",
                    channel_type=self.channel_type,
                )
            )
        key: str = kwargs["body"]
        lead_command = "/lead"
        if key.strip() == lead_command:
            msg = self.env._(
                "Create a new lead with: "
                "%(pre_start)s%(lead_command)s %(i_start)slead title%(i_end)s%(pre_end)s",
                lead_command=lead_command,
                pre_start=Markup("<pre>"),
                pre_end=Markup("</pre>"),
                i_start=Markup("<i>"),
                i_end=Markup("</i>"),
            )
            self.env.user._bus_send_transient_message(self, msg)
            return
        lead = self._convert_visitor_to_lead(self.env.user.partner_id, key)
        msg = Markup(
            '<div class="o_mail_notification" data-oe-type="create-lead">%s</div>',
        ) % self.env._("created a new lead: %s", lead._get_html_link())
        self.message_post(body=msg, subtype_xmlid="mail.mt_comment")

    def _convert_visitor_to_lead(self, partner, key):
        """ Create a lead from channel /lead command
        :param partner: internal user partner (operator) that created the lead;
        :param key: operator input in chat ('/lead Lead about Product')
        """
        return self.env["crm.lead"].create(self._prepare_channel_lead_create_vals(partner, key))

    def _prepare_channel_lead_create_vals(self, partner, key):
        return {
            "description": self._get_channel_history(),
            "name": html2plaintext(key[5:]),
            "origin_channel_id": self.id,
            "partner_id": False,
            "referred": partner.name,
            "team_id": False,
            "user_id": False,
        }

    def _types_allowing_create_lead(self):
        """ Return the channel types which allow lead creation """
        return []
