# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard
from . import tools


def _account_peppol_post_init(env):
    for company in env['res.company'].sudo().search([]):
        env['ir.default'].set('res.partner', 'peppol_verification_state', 'not_verified', company_id=company.id)

    if env['ir.config_parameter'].sudo().get_bool('database.is_neutralized'):
        env['ir.config_parameter'].sudo().set_str('account_peppol.edi.mode', 'demo')
