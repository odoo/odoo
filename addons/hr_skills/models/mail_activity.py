from odoo import fields, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    certification_skill_id = fields.Many2one(
        comodel_name="hr.skill",
        index="btree_not_null",
        ondelete="set null",
    )
    certification_skill_level_id = fields.Many2one(
        comodel_name="hr.skill.level",
        ondelete="set null",
    )
