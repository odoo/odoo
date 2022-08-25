# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Skill(models.Model):
    _name = 'hr.skill'
    _description = "Skill"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    skill_type_id = fields.Many2one('hr.skill.type', required=True, ondelete='cascade')

    def name_get(self):
        if not self._context.get('from_skill_dropdown'):
            return super().name_get()
        return [(record.id, f"{record.name} ({record.skill_type_id.name})") for record in self]
