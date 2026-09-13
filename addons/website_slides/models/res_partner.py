from odoo import _, api, fields, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = "res.partner"

    slide_channel_partner_ids = fields.One2many(
        comodel_name="slide.channel.partner",
        inverse_name="partner_id",
        string="eLearning Memberships",
        groups="website_slides.group_website_slides_officer",
    )
    slide_channel_ids = fields.Many2many(
        comodel_name="slide.channel",
        string="eLearning Courses",
        compute="_compute_slide_channel_values",
        search="_search_slide_channel_ids",
        groups="website_slides.group_website_slides_officer",
    )
    slide_channel_completed_ids = fields.One2many(
        comodel_name="slide.channel",
        string="Completed Courses",
        compute="_compute_slide_channel_values",
        search="_search_slide_channel_completed_ids",
        groups="website_slides.group_website_slides_officer",
    )
    slide_channel_count = fields.Integer(
        string="Course Count",
        compute="_compute_slide_channel_values",
        groups="website_slides.group_website_slides_officer",
    )
    slide_channel_company_count = fields.Integer(
        string="Company Course Count",
        compute="_compute_slide_channel_company_count",
        groups="website_slides.group_website_slides_officer",
    )

    @api.depends(
        "slide_channel_partner_ids.channel_id",
        "slide_channel_partner_ids.member_status",
        "slide_channel_partner_ids.active",
    )
    def _compute_slide_channel_values(self):
        data = {
            (partner.id, member_status): channel_ids
            for partner, member_status, channel_ids in self.env["slide.channel.partner"]
            .sudo()
            ._read_group(
                domain=[
                    ("partner_id", "in", self.ids),
                    ("member_status", "!=", "invited"),
                ],
                groupby=["partner_id", "member_status"],
                aggregates=["channel_id:array_agg"],
            )
        }

        for partner in self:
            slide_channel_ids = (
                data.get((partner.id, "joined"), [])
                + data.get((partner.id, "ongoing"), [])
                + data.get((partner.id, "completed"), [])
            )
            partner.slide_channel_ids = slide_channel_ids
            partner.slide_channel_completed_ids = self.env["slide.channel"].browse(
                data.get((partner.id, "completed"), [])
            )
            partner.slide_channel_count = len(slide_channel_ids)

    def _search_slide_channel_completed_ids(self, operator, value):
        subquery = (
            self.env["slide.channel.partner"]
            .sudo()
            ._search(
                [("channel_id", operator, value), ("member_status", "=", "completed")]
            )
        )
        return [("id", "in", subquery.subselect("partner_id"))]

    def _search_slide_channel_ids(self, operator, value):
        subquery = (
            self.env["slide.channel.partner"]
            .sudo()
            ._search(
                [("channel_id", operator, value), ("member_status", "!=", "invited")]
            )
        )
        return [("id", "in", subquery.subselect("partner_id"))]

    @api.depends("is_company", "child_ids.slide_channel_count")
    def _compute_slide_channel_company_count(self):
        companies = self.filtered("is_company")
        channels = self.env["slide.channel"].sudo()
        if companies:
            channels = channels.search([("partner_ids", "in", companies.child_ids.ids)])
        for partner in self:
            if partner.is_company:
                children = set(partner.child_ids.ids)
                partner.slide_channel_company_count = sum(
                    1 for channel in channels if children & set(channel.partner_ids.ids)
                )
            else:
                partner.slide_channel_company_count = 0

    def action_view_courses(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "website_slides.slide_channel_partner_action"
        )
        action["display_name"] = _("Courses")
        action["domain"] = [("member_status", "!=", "invited")]
        if len(self) == 1 and self.is_company:
            action["domain"] = Domain.AND(
                [action["domain"], [("partner_id", "in", self.child_ids.ids)]]
            )
        elif len(self) == 1:
            action["context"] = {"search_default_partner_id": self.id}
        else:
            action["domain"] = Domain.AND(
                [action["domain"], [("partner_id", "in", self.ids)]]
            )
        return action
