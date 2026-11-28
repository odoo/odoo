# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from odoo.addons.mail.tools.discuss import Store

from odoo import api, fields, models, _


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

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
        key = kwargs['body']
        lead_command = "/lead"
        if key.strip() == lead_command:
            msg = _(
                "Create a new lead with: "
                "%(pre_start)s%(lead_command)s %(i_start)slead title%(i_end)s%(pre_end)s",
                lead_command=lead_command,
                pre_start=Markup("<pre>"),
                pre_end=Markup("</pre>"),
                i_start=Markup("<i>"),
                i_end=Markup("</i>"),
            )
            self.env.user._bus_send_transient_message(self, msg)
        else:
            lead = self._convert_visitor_to_lead(self.env.user.partner_id, key)
            msg = Markup(
                '<div class="o_mail_notification" data-oe-type="create-lead">%s</div>',
            ) % self.env._("created a new lead: %s", lead._get_html_link_with_href())
<<<<<<< 67611077d3eee3553491e6e6a8afe5d538dbeb7b
            self.message_post(body=msg, message_type='notification')
||||||| 041d8165ba5cf322c773cd4e39f8cf1170252af8
            self.message_post(body=msg, subtype_xmlid="mail.mt_comment")
=======
            self.message_post(body=msg, subtype_xmlid="mail.mt_comment")
            Store(bus_channel=self.env.user).add(
                self, "_store_livechat_extra_fields",
            )
>>>>>>> 0e68769c01db3d345b2cc84014b32385b9319066

    def _convert_visitor_to_lead(self, partner, key):
        """ Create a lead from channel /lead command
        :param partner: internal user partner (operator) that created the lead;
        :param key: operator input in chat ('/lead Lead about Product')
        """
        return self.env["crm.lead"].create(self._prepare_lead_create_values(partner, key))

    def _prepare_lead_create_values(self, partner, key):
        customer = self.livechat_customer_partner_ids[:1]
        if not customer and "whatsapp_partner_id" in self._fields:
            customer = self.whatsapp_partner_id
        values = super()._prepare_lead_create_values(partner, key)
        values["origin_channel_id"] = self.id
        values["partner_id"] = customer.id
        values["description"] = self._get_channel_history()
        if self.channel_type == "livechat":
            values["source_id"] = self.env["utm.mixin"]._utm_ref("utm.utm_source_livechat").id
            values["medium_id"] = self.env["utm.mixin"]._utm_ref("utm.utm_medium_website").id
        return values

    def _store_livechat_extra_fields(self, res: Store.FieldList):
        super()._store_livechat_extra_fields(res)
        if not self.env["crm.lead"].has_access("read"):
            return
        leads = self.env["crm.lead"].search_fetch(
            [("partner_id", "in", self.livechat_customer_partner_ids.ids)], ["name", "partner_id"],
        )
        res.many(
            "livechat_customer_partner_ids",
            lambda res: res.many(
                "opportunity_ids",
                ["name"],
                value=lambda partner: leads.filtered(lambda lead: lead.partner_id == partner),
            ),
            only_data=True,
        )
