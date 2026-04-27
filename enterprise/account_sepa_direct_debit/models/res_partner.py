# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    sdd_mandate_ids = fields.One2many(comodel_name='sdd.mandate', inverse_name='partner_id',
        help="Every mandate belonging to this partner.")
    sdd_count = fields.Integer(compute='_compute_sdd_count', string="SDD count")

    def _compute_sdd_count(self):
        sdd_data = self.env['sdd.mandate']._read_group(
            domain=[('partner_id', 'in', self.ids)],
            groupby=['partner_id'],
            aggregates=['__count'])
        mapped_data = {partner.id: count for partner, count in sdd_data}
        for partner in self:
            partner.sdd_count = mapped_data.get(partner.id, 0)
