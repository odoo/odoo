# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.api import Environment, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


def update_companies_country(cr, registry):
    _logger.info('Force installation l10n_ar module')
    env = Environment(cr, SUPERUSER_ID, {})
    module_ids = env['ir.module.module'].search([
        ('name', '=', 'l10n_ar'), ('state', '=', 'uninstalled')])
    module_ids.sudo().button_install()


def post_init_hook(cr, registry):
    _logger.info('Post init hook initialized')
    update_companies_country(cr, registry)
