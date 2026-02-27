from odoo import models

from .template_be import BE_TEMPLATE_CODES, BE_ASSO_TEMPLATE_CODES, BE_COMP_TEMPLATE_CODES


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _chart_template_selection(self):
        if self.chart_template in BE_TEMPLATE_CODES and self.root_id._existing_accounting():
            available_templates = BE_ASSO_TEMPLATE_CODES if self.chart_template in BE_ASSO_TEMPLATE_CODES else BE_COMP_TEMPLATE_CODES
            return [
                (template_code, template['name'])
                for template_code, template in self.env['account.chart.template']._get_chart_template_mapping(get_all=False).items()
                if template_code in available_templates
            ]
        return super()._chart_template_selection()
