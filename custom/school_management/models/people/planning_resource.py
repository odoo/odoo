# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    teacher_id = fields.Many2one("university.teacher", string="Teacher", index=True)
    role = fields.Char(string="Role", compute="_compute_role", store=True, readonly=False)
    weekly_capacity_hours = fields.Float(string="Weekly Capacity Hours", default=40.0)

    @api.depends("teacher_id", "teacher_id.title", "teacher_id.position", "resource_type")
    def _compute_role(self):
        for res in self:
            if res.teacher_id:
                title = res.teacher_id.title or ""
                position = res.teacher_id.position or ""
                if position:
                    role_str = position.replace("_", " ").title()
                elif title:
                    role_str = title.upper() if title in ["dr", "prof"] else title.title()
                else:
                    role_str = "Instructor"
                res.role = role_str
            else:
                res.role = "Resource"


class UniversityTeacher(models.Model):
    _inherit = "university.teacher"

    resource_id = fields.Many2one("resource.resource", string="Planning Resource", copy=False, index=True)

    def _get_or_create_resource(self):
        self.ensure_one()
        if self.resource_id:
            return self.resource_id
        Resource = self.env["resource.resource"].sudo()
        existing = Resource.search([("teacher_id", "=", self.id)], limit=1)
        if not existing:
            existing = Resource.create({
                "name": self.name,
                "resource_type": "user",
                "user_id": self.user_id.id if self.user_id else False,
                "teacher_id": self.id,
                "weekly_capacity_hours": 35.0,
            })
        self.resource_id = existing.id
        return existing
