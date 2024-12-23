# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard
from . import tools

def _account_peppol_pre_init(env):
    view = env.ref('account_edi_ubl_cii.view_partner_property_form')
    if "peppol_address" not in view.arch:
        view.reset_arch(mode='hard')

def _account_peppol_post_init(env):
    for company in env['res.company'].sudo().search([]):
        env['ir.default'].set('res.partner', 'peppol_verification_state', 'not_verified', company_id=company.id)
