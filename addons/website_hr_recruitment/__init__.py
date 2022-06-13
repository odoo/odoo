# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, SUPERUSER_ID

from . import controllers
from . import models

def _activate_frontend_filters(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    views = {
        'department': env.ref('website_hr_recruitment.job_filter_by_departments'),
        'office': env.ref('website_hr_recruitment.job_filter_by_offices'),
        'country': env.ref('website_hr_recruitment.job_filter_by_countries'),
    }
    jobs = env['hr.job'].search([])
    for key, view in views.items():
        if view.active:
            continue
        # Activate department if more than 1
        # Activate Office/Country if more than 1 (Remote included)
        if key == 'department' and len(jobs.department_id) > 1:
            view.active = True
        elif key == 'office' and len(list(set(j.address_id for j in jobs))) > 1:
            view.active = True
        elif key == 'country' and len(list(set(j.address_id.country_id for j in jobs if j.address_id.country_id))) > 1:
            view.active = True
