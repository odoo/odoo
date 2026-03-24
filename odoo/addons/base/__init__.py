# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.safe_eval import safe_whitelist

from . import models
from . import report
from . import wizard


def post_init(env):
    """Rewrite ICP's to force groups"""
    env['ir.config_parameter'].init(force=True)


safe_whitelist.add_instance('odoo.addons.base.models.ir_qweb.QWebError')
safe_whitelist.add_instance('odoo.addons.base.models.ir_qweb.QwebContent')
safe_whitelist.add_instance('odoo.addons.base.models.ir_qweb.QwebJSON')
safe_whitelist.add_instance('odoo.addons.base.models.res_lang.LangDataDict')
safe_whitelist.add_function('odoo.addons.base.models.ir_actions.LoggerProxy.error')
safe_whitelist.add_function('odoo.addons.base.models.ir_actions.LoggerProxy.exception')
safe_whitelist.add_function('odoo.addons.base.models.ir_actions.LoggerProxy.info')
safe_whitelist.add_function('odoo.addons.base.models.ir_actions.LoggerProxy.log')
safe_whitelist.add_function('odoo.addons.base.models.ir_actions.LoggerProxy.warning')
safe_whitelist.add_function('odoo.addons.base.models.ir_actions_report.IrActionsReport._render_template.<locals>.*')
safe_whitelist.add_function('odoo.addons.base.models.ir_qweb.generate_functions.<locals>.*')  # `__name__` is present in globals for Qweb compiled template
safe_whitelist.add_function('odoo.addons.base.models.ir_qweb.keep_query')
safe_whitelist.add_function('odoo.addons.base.models.res_partner._tz_get')
safe_whitelist.add_function('odoo.addons.base.models.ir_qweb.test.<locals>.*')
safe_whitelist.add_function('odoo.addons.base.tests.test_ir_qweb.TestQWebBasic.test_compile_expr.<locals>.*')
