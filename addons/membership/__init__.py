# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def _membership_post_init(env):
    # Need to initialize config parameter if the installation was not done with the settings of CRM
    if not env['ir.config_parameter'].sudo().get_param('crm.membership_type'):
        env['ir.config_parameter'].sudo().set_param('crm.membership_type', 'Member')
