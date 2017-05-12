# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ir
import workflow
import module
import res
import report
import tests

def post_init(cr, registry):
    """Rewrite ICP's to force groups"""
    from odoo import api, SUPERUSER_ID
    from odoo.addons.base.ir.ir_config_parameter import _default_parameters

    env = api.Environment(cr, SUPERUSER_ID, {})
    ICP = env['ir.config_parameter']
    for key, func in _default_parameters.iteritems():
        val = ICP.get_param(key)
        _, groups = func()
        ICP.set_param(key, val, groups)
