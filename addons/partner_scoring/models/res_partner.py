from odoo import api, fields, models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "mixin.scored"]

    _score_line_model = "partner.score.line"

    # Fields that can move a partner in or out of being the commercial entity.
    _COMMERCIAL_FIELDS = ("parent_id", "is_company", "type")

    attribute_line_ids = fields.One2many(
        comodel_name="res.partner.attribute.line",
        inverse_name="partner_id",
        string="Profile attributes",
    )
    tier_id = fields.Many2one(
        comodel_name="partner.tier",
        string="Commercial Tier",
        compute="_compute_tier_id",
        compute_sudo=True,
        recursive=True,
        store=True,
        tracking=True,
        help="First active tier whose score range contains the partner's "
        "score. A partner that was never scored carries no tier: a tier means "
        "a measurement was taken. A contact carries its commercial entity's "
        "tier: the score describes the customer, not the person. Tracked, so "
        "the chatter carries the band history. score is deliberately not "
        "tracked: it moves on every catalog edit and every attribute capture, "
        "and would bury the transitions that carry commercial meaning.",
    )
    factor = fields.Float(
        related="tier_id.factor",
        string="Tier Factor",
        readonly=True,
    )
    score_line_ids = fields.One2many(
        comodel_name="partner.score.line",
        inverse_name="subject_id",
        string="Score Breakdown",
    )
    score_line_count = fields.Count(
        count_of="score_line_ids",
        string="Score Rows",
        store=True,
        help="How many audit rows explain the score. Stored so the partner "
        "form can decide whether to offer the breakdown without loading "
        "every row of it.",
    )

    def write(self, vals):
        result = super().write(vals)
        if any(field in vals for field in self._COMMERCIAL_FIELDS):
            self.env["res.partner.attribute.line"]._follow_commercial_partner(self)
        return result

    def _score_classification_fields(self):
        return ["tier_id"]

    @api.depends(
        "score",
        "score_line_count",
        "company_id",
        "commercial_partner_id",
        "commercial_partner_id.tier_id",
    )
    def _compute_tier_id(self):
        tier_model = self.env["partner.tier"]
        commercial = self.filtered(lambda p: p.commercial_partner_id == p)
        for partner in commercial:
            # The partner's own company, never the acting user's: this field is
            # stored and shared, so falling back to env.company would store
            # whichever scale the last user to trigger the compute happened to
            # be in. A company-less partner resolves against company-less bands.
            partner.tier_id = (
                tier_model._classify(partner.score, partner.company_id)
                if partner.score_line_count
                else tier_model
            )
        for partner in self - commercial:
            partner.tier_id = partner.commercial_partner_id.tier_id

    def _score_observe_partner_attr(self, dimension):
        self.check_singleton()
        return self.attribute_line_ids
