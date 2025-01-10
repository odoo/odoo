# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartnerGrade(models.Model):
    _name = 'res.partner.grade'
    _order = 'sequence'
    _description = 'Partner Grade'

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    name = fields.Char('Level Name', translate=True)
    membership_label = fields.Char(compute='_compute_membership_label')
    members_count = fields.Integer(compute='_compute_members_count')

    def _compute_membership_label(self):
        if self.env['ir.config_parameter'].sudo().get_param('crm.membership_type') == 'Partner':
            self.membership_label = self.env._("Partners")
        else:
            self.membership_label = self.env._("Members")

    def _compute_members_count(self):
        partners_data = self.env['res.partner']._read_group(
            domain=[('grade_id', 'in', self.ids)],
            groupby=['grade_id'],
            aggregates=['__count'],
        )
        mapped_data = {grade.id: count for grade, count in partners_data}
        for grade in self:
            grade.members_count = mapped_data.get(grade.id, 0)
