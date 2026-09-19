from odoo import api, fields, models


class SlideSlidePartner(models.Model):
    _name = "slide.slide.partner"
    _description = "Slide / Partner decorated m2m"
    _table = "slide_slide_partner"
    _rec_name = "partner_id"

    slide_id = fields.Many2one(
        comodel_name="slide.slide",
        string="Content",
        index=True,
        required=True,
        ondelete="cascade",
    )
    slide_category = fields.Selection(related="slide_id.slide_category")
    channel_id = fields.Many2one(  # noqa: E8529  One2many inverse, cascading FK
        comodel_name="slide.channel",
        related="slide_id.channel_id",
        string="Channel",
        store=True,
        index=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        index=True,
        required=True,
        ondelete="cascade",
    )
    vote = fields.Integer(default=0)
    completed = fields.Boolean()
    quiz_attempts_count = fields.Integer(
        string="Quiz attempts count",
        default=0,
    )

    _slide_partner_uniq = models.Constraint(
        "unique(slide_id, partner_id)",
        "A partner membership to a slide must be unique!",
    )
    _check_vote = models.Constraint(
        "CHECK(vote IN (-1, 0, 1))",
        "The vote must be 1, 0 or -1.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        completed = res.filtered("completed")
        if completed:
            completed._recompute_completion()
        return res

    def write(self, vals):
        slides_completion_to_recompute = self.env["slide.slide.partner"]
        if "completed" in vals:
            slides_completion_to_recompute = self.filtered(
                lambda slide_partner: slide_partner.completed != vals["completed"]
            )

        res = super().write(vals)

        if slides_completion_to_recompute:
            slides_completion_to_recompute._recompute_completion()

        return res

    def unlink(self):
        channel_ids = self.channel_id.ids
        partner_ids = self.partner_id.ids
        res = super().unlink()
        self.env["slide.channel.partner"].search(
            [
                ("channel_id", "in", channel_ids),
                ("partner_id", "in", partner_ids),
                ("member_status", "not in", ("completed", "invited")),
            ]
        )._recompute_completion()
        return res

    def _recompute_completion(self):
        self.env["slide.channel.partner"].search(
            [
                ("channel_id", "in", self.channel_id.ids),
                ("partner_id", "in", self.partner_id.ids),
                ("member_status", "not in", ("completed", "invited")),
            ]
        )._recompute_completion()
