# -*- coding: utf-8 -*-

from . import models
from . import wizard
from . import controllers

from odoo import api, SUPERUSER_ID, _

def _initialize_contact_logs(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for partner in env['res.partner'].search([]):
        partner.message_post(body=_("Contact created"), subtype_xmlid='mail.mt_note', **{'create_date': partner.create_date})
