# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import controllers
import models
import report
import wizard


from odoo import api, SUPERUSER_ID


# TODO: Apply proper fix & remove in master
def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.model.data'].search([
        ('model', 'like', '%stock%'),
        ('module', '=', 'stock')
    ]).unlink()
