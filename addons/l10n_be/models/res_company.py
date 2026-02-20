from odoo import models


BELGIAN_CHARTS = ['be_asso_abbr', 'be_asso_full', 'be_comp_abbr_cap', 'be_comp_abbr_con', 'be_comp_full_cap', 'be_comp_full_con']


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _chart_template_selection(self):
        if self.root_id and self.root_id._existing_accounting() and self.chart_template in BELGIAN_CHARTS:
            module = self.env.ref('base.module_l10n_be')
            if module.state != 'installable':
                selection = []
                prefix = 'be_asso' if self.chart_template.startswith('be_asso') else 'be_comp'
                for template_code, template in module.account_templates.items():
                    if template_code.startswith(prefix) and template['visible']:
                        selection.append((template_code, template['name']))
                return selection
        return super()._chart_template_selection()
