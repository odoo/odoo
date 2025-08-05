# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

# DONE
class HrSkill(models.Model):
    _name = 'hr.skill'
    _description = "Skill"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    skill_type_id = fields.Many2one('hr.skill.type', required=True, index=True, ondelete='cascade')
    color = fields.Integer(related='skill_type_id.color')

    @api.depends('skill_type_id')
    @api.depends_context('from_skill_dropdown')
    def _compute_display_name(self):
        if not self.env.context.get('from_skill_dropdown'):
            return super()._compute_display_name()
        for record in self:
            record.display_name = f"{record.name} ({record.skill_type_id.name})"
