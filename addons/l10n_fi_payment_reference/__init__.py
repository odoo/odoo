# -*- coding: utf-8 -*-
##############################################################################
#
#    ODOO Open Source Management Solution
#
#    ODOO Addon module by Sprintit Ltd
#    Copyright (C) 2018 Sprintit Ltd (<http://sprintit.fi>).
#
##############################################################################

from odoo import api, SUPERUSER_ID

from . import models


def set_default_reference_type(cr, reqistry):
    'When installing this module to existing database this function will handle the transition'
    print("""
    ###
    ###
    ###
    ###  Setting default reference type to Finnish Bank Reference
    ###
    ###
    ###
    """)
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        companies = env['res.company'].search([])
        for company in companies:
            company.invoice_reference_type = 'fi_bank_reference'

    return