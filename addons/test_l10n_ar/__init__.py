# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.api import Environment, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


def install_l10n_ar(cr, registry):
    _logger.info('Force installation l10n_ar module')
    env = Environment(cr, SUPERUSER_ID, {})
    module_ids = env['ir.module.module'].search([
        ('name', '=', 'l10n_ar'), ('state', '=', 'uninstalled')])
    module_ids.sudo().button_install()

def set_user_company(cr, registry):
    _logger.info('Set user company to main company to avoid unit test errors')
    env = Environment(cr, SUPERUSER_ID, {})
    users = env.ref('base.user_root')
    users |= env.ref('base.user_admin')
    users |= env.ref('base.user_demo')
    users.write({'company_id': env.ref('base.main_company').id})

def post_init_hook(cr, registry):
    _logger.info('Post init hook initialized')
    install_l10n_ar(cr, registry)
    set_user_company(cr, registry)
