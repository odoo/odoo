# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrSkillLevel(models.Model):
    _name = 'hr.skill.level'
    _description = "Skill Level"
    _order = "level_progress"

    skill_type_id = fields.Many2one('hr.skill.type', index='btree_not_null', ondelete='cascade')
    name = fields.Char(required=True)
    level_progress = fields.Integer(string="Progress", help="Progress from zero knowledge (0%) to fully mastered (100%).")
    default_level = fields.Boolean(help="If checked, this level will be the default one selected when choosing this skill.")

    # This field is a technical field, created to be set exclusively by the front-end; it's why this computed field is
    # not stored and not readonly.
    # With this field, it's possible to know in onchange defined in the model hr_skill_type which
    # level became the new default_level.
    technical_is_new_default = fields.Boolean(compute="_compute_technical_is_new_default", readonly=False)

    _check_level_progress = models.Constraint(
        'CHECK(level_progress BETWEEN 0 AND 100)',
        'Progress should be a number between 0 and 100.',
    )

    # This compute is never trigger by a depends in purpose. The front-end will change this value when the
    # default_level will become true.
    def _compute_technical_is_new_default(self):
        self.technical_is_new_default = False

    @api.model_create_multi
    def create(self, vals_list):
        skill_levels = super().create(vals_list)
        for level in skill_levels:
            if level.default_level:
                level.skill_type_id.skill_level_ids.filtered(lambda r: r.id != level.id).default_level = False
        return skill_levels

    def write(self, vals):
        res = super().write(vals)
        if vals.get('default_level'):
            self.skill_type_id.skill_level_ids.filtered(lambda r: r.id != self.id).default_level = False
        return res
