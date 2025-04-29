from odoo import fields, models


class HrSkillMixin(models.AbstractModel):
    """
    Mixin for adding skills to any model :D
    """

    _name = "hr.skill.mixin"
    _description = "HR Skill Mixin"

    composite_skill_ids = fields.Many2many("hr.skill.composite")
