# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.tools import convert


class HrAppraisal(models.Model):
    _inherit = 'hr.appraisal'

    def _load_demo_data(self):
        super()._load_demo_data()
        convert.convert_file(self.env, 'hr_appraisal_skills', 'demo/scenarios/scenario_appraisal_demo.xml', None,
            mode='init', kind='data')
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
