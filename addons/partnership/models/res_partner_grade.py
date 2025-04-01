# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartnerGrade(models.Model):
    _name = 'res.partner.grade'
    _order = 'sequence'
    _description = 'Partner Grade'

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    name = fields.Char('Level Name', translate=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    default_pricelist_id = fields.Many2one('product.pricelist')
    partners_count = fields.Integer(compute='_compute_partners_count')
    partners_label = fields.Char(related='company_id.partnership_label')

    def _compute_partners_count(self):
        partners_data = self.env['res.partner']._read_group(
            domain=[('grade_id', 'in', self.ids)],
            groupby=['grade_id'],
            aggregates=['__count'],
        )
        mapped_data = {grade.id: count for grade, count in partners_data}
        for grade in self:
            grade.partners_count = mapped_data.get(grade.id, 0)
