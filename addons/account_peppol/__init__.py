# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import tools


def _account_peppol_post_init(env):
    for company in env['res.company'].sudo().search([]):
        env['ir.property']._set_default('peppol_verification_state', 'res.partner', 'not_verified', company)
