# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def post_init_hook(env):
    if 'documents_hr' in env['ir.module.module'].sudo()._installed():
        fleet_string = env._('Fleet')
        for company in env['res.company'].search([('employee_subfolders', 'not ilike', fleet_string)]):
            if company.employee_subfolders:
                subfolders = company.employee_subfolders.split(',')
                subfolders.append(fleet_string)
            else:
                subfolders = [fleet_string]
            company.employee_subfolders = ','.join(subfolders)
