from odoo import api, fields, models
from odoo.fields import Domain


class HrSkillProficiency(models.Model):
    _name = 'hr.skill.proficiency'
    _description = "Skill Proficiency"
    _order = "skill_type_id, skill_id, skill_level_id"
    _rec_name = "skill_id"

    skill_id = fields.Many2one('hr.skill', required=True, ondelete='cascade', index=True)
    skill_level_id = fields.Many2one('hr.skill.level', required=True, ondelete='cascade', index=True)
    skill_type_id = fields.Many2one('hr.skill.type', related='skill_id.skill_type_id', store=True)

    _skill_level_uniq = models.Constraint(
        'unique(skill_id, skill_level_id)',
        'A proficiency record already exists for this skill and level combination.'
    )

    @api.depends('skill_id', 'skill_level_id')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.skill_id.name}: {record.skill_level_id.name}"

    @api.model
    def _search_display_name(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        if ': ' in (value or ''):
            skill_name, level_name = value.split(': ', 1)
            return Domain.AND([
                Domain('skill_id.name', operator, skill_name),
                Domain('skill_level_id.name', operator, level_name),
            ])
        return Domain.OR([
            Domain('skill_id.name', operator, value),
            Domain('skill_level_id.name', operator, value),
        ])

    @api.model
    def _get_or_create_proficiencies(self, skill_lines):
        pairs = {
            (line.skill_id.id, line.skill_level_id.id) for line in skill_lines
        }
        if not pairs:
            return self.browse()

        skill_ids = [p[0] for p in pairs]
        level_ids = [p[1] for p in pairs]
        existing = self.search([
            ('skill_id', 'in', skill_ids),
            ('skill_level_id', 'in', level_ids),
        ])
        existing_map = {(p.skill_id.id, p.skill_level_id.id): p for p in existing}
        missing = pairs - existing_map.keys()
        if missing:
            new_profs = self.sudo().create([
                {'skill_id': sid, 'skill_level_id': lid}
                for sid, lid in missing
            ])
            for prof in new_profs:
                existing_map[prof.skill_id.id, prof.skill_level_id.id] = prof

        return self.browse([existing_map[pair].id for pair in pairs])
