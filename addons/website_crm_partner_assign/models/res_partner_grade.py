from odoo import fields, models


class ResPartnerGrade(models.Model):
    _name = "res.partner.grade"
    _inherit = ["res.partner.grade", "mixin.website.published"]

    partner_weight = fields.Integer(
        string="Level Weight",
        default=1,
        help="Gives the probability to assign a lead to this partner. (0 means no assignment.)",
    )

    def _compute_website_url(self):
        super()._compute_website_url()
        for grade in self:
            grade.website_url = "/partners/grade/%s" % (
                self.env["ir.http"]._slug(grade)
            )

    def _default_is_published(self):
        return True
