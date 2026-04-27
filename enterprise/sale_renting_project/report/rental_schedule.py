# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class RentalSchedule(models.Model):
    _inherit = 'sale.rental.schedule'

    project_id = fields.Many2one('project.project', readonly=True)

    def _select(self) -> SQL:
        return SQL("""%s,
            s.project_id as project_id
        """, super()._select())

    def _groupby(self) -> SQL:
        return SQL("""%s,
            s.project_id
        """, super()._groupby())
