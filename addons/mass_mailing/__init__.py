# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard
from odoo import api, SUPERUSER_ID


def update_admin_contact(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    contact = env.ref('mass_mailing.mass_mailing_contact_0')
    contact.name = env.ref('base.user_admin').name
    contact.email = env.ref('base.user_admin').email
