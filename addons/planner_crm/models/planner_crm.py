from openerp import api, models

class PlannerCrm(models.Model):
    _inherit = 'planner.planner'

    @api.model
    def _prepare_planner_crm_data(self):
        id = self.env['ir.model.data'].xmlid_to_res_id('sales_team.section_sales_department')
        alias_domain = self.env['crm.case.section'].browse(id).alias_domain
        company_data = self.env['res.users'].browse(self._uid).company_id
        values = {
            'prepare_backend_url': self.prepare_backend_url,
            'alias_domain': alias_domain,
            'company_data': company_data,
        }
        return values