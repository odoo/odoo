# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def post_init_hook(env):
    env['ir.config_parameter'].sudo().set_str('report.pdf_engine_default', 'wkhtmltopdf')
