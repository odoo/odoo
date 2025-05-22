# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrApplicantSkill(models.Model):
    _name = 'hr.applicant.skill'
    _description = "Skill level for an applicant"
    _rec_name = 'skill_id'
    _order = "skill_level_id"

    applicant_id = fields.Many2one(
        comodel_name='hr.applicant',
        required=True,
        index=True,
        ondelete='cascade')
    skill_id = fields.Many2one(
        comodel_name='hr.skill',
        compute='_compute_skill_id',
        store=True,
        domain="[('skill_type_id', '=', skill_type_id)]",
        readonly=False,
        required=True)
    skill_level_id = fields.Many2one(
        comodel_name='hr.skill.level',
        compute='_compute_skill_level_id',
        domain="[('skill_type_id', '=', skill_type_id)]",
        store=True,
        readonly=False,
        required=True)
    skill_type_id = fields.Many2one(
        comodel_name='hr.skill.type',
        required=True)
    level_progress = fields.Integer(
        related='skill_level_id.level_progress')

    _unique_skill = models.Constraint(
        'unique (applicant_id, skill_id)',
        'Two levels for the same skill is not allowed',
    )

    @api.constrains('skill_id', 'skill_type_id')
    def _check_skill_type(self):
        for applicant_skill in self:
            if applicant_skill.skill_id not in applicant_skill.skill_type_id.skill_ids:
                raise ValidationError(_("The skill %(name)s and skill type %(type)s doesn't match", name=applicant_skill.skill_id.name, type=applicant_skill.skill_type_id.name))

    @api.constrains('skill_type_id', 'skill_level_id')
    def _check_skill_level(self):
        for applicant_skill in self:
            if applicant_skill.skill_level_id not in applicant_skill.skill_type_id.skill_level_ids:
                raise ValidationError(_("The skill level %(level)s is not valid for skill type: %(type)s", level=applicant_skill.skill_level_id.name, type=applicant_skill.skill_type_id.name))

    @api.depends('skill_type_id')
    def _compute_skill_id(self):
        for applicant_skill in self:
            if applicant_skill.skill_id.skill_type_id != applicant_skill.skill_type_id:
                applicant_skill.skill_id = False

    @api.depends('skill_id')
    def _compute_skill_level_id(self):
        for applicant_skill in self:
            if not applicant_skill.skill_id:
                applicant_skill.skill_level_id = False
            else:
                skill_levels = applicant_skill.skill_type_id.skill_level_ids
                applicant_skill.skill_level_id = skill_levels.filtered('default_level') or skill_levels[0] if skill_levels else False
