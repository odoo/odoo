# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def post_init_hook(env):
    env.cr.execute("""
        UPDATE res_company
        SET report_rendering_engine = 'paper-muncher'
        WHERE report_rendering_engine = 'html'
    """)
