from odoo import api, models
from odoo.fields import Domain


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.depends('country_id')
    def _compute_domestic_fiscal_position_id(self):
        super()._compute_domestic_fiscal_position_id()
        for company in self.filtered(lambda comp: comp.root_id.chart_template == 'mq'):
            local_fps = company.fiscal_position_ids.filtered_domain(
                Domain('country_id', '=', company.country_id.id) |
                Domain([('country_id', '=', False), ('country_group_id', 'in', company.country_id.country_group_ids.ids)])
            ).sorted('sequence')
            if local_fps:
                company.domestic_fiscal_position_id = local_fps[0]
