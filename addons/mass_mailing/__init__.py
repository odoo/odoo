# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from odoo import api, SUPERUSER_ID


def _init_update_admin_contact(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    contact = env.ref('mass_mailing.mass_mailing_contact_0', raise_if_not_found=False)
    if contact:
        user_admin = env.ref('base.user_admin')
        contact.write({
            'company_name': user_admin.commercial_company_name,
            'country_id': user_admin.country_id.id,
            'email': user_admin.email,
            'name': user_admin.name,
            'title_id': user_admin.title.id,
        })
