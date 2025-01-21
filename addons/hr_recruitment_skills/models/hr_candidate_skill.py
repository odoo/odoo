# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrCandidateSkill(models.Model):
    _name = 'hr.candidate.skill'
    _description = "Skill level for a candidate"
    _rec_name = 'skill_id'
    _order = "skill_level_id"

    candidate_id = fields.Many2one(
        comodel_name='hr.candidate',
        required=True,
        ondelete='cascade')
    skill_id = fields.Many2one(
        comodel_name='hr.skill',
        required=True)
    skill_type_id = fields.Many2one(
        comodel_name='hr.skill.type',
        related='skill_id.skill_type_id')
    skill_level_id = fields.Many2one(
        comodel_name='hr.skill.level',
        compute='_compute_skill_level_id',
        domain="[('skill_type_id', '=', skill_type_id)]",
        store=True,
        readonly=False,
        required=True)
    level_progress = fields.Integer(
        related='skill_level_id.level_progress')

    __unique_skill = models.Constraint(
        'unique (candidate_id, skill_id)',
        'Two levels for the same skill is not allowed',
    )

    @api.constrains('skill_id', 'skill_level_id')
    def _check_skill_level(self):
        for candidate_skill in self:
            if candidate_skill.skill_level_id not in candidate_skill.skill_type_id.skill_level_ids:
                raise ValidationError(_("The skill level %(level)s is not valid for skill type: %(type)s", level=candidate_skill.skill_level_id.name, type=candidate_skill.skill_type_id.name))

    @api.depends('skill_id')
    def _compute_skill_level_id(self):
        for candidate_skill in self:
            if not candidate_skill.skill_id:
                candidate_skill.skill_level_id = False
            else:
                skill_levels = candidate_skill.skill_type_id.skill_level_ids
                candidate_skill.skill_level_id = skill_levels.filtered('default_level') or skill_levels[0] if skill_levels else False
