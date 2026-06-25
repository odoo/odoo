from odoo import api, models, fields


class TourGroupMember(models.Model):
    _name = "tour.group.member"
    _description = "Tour Group Member"

    booking_id = fields.Many2one("tour.booking", required=True, ondelete="cascade")
    name = fields.Char(required=True)
    age = fields.Integer()
    is_child = fields.Boolean(compute="_compute_is_child", store=True)
    nationality = fields.Char()
    special_requirement = fields.Text()

    @api.depends("age")
    def _compute_is_child(self):
        for member in self:
            member.is_child = member.age < 18
