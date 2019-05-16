# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.api import Environment, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


def update_companies_country(cr, registry):
    _logger.info('Update update_companies_country to AR')
    env = Environment(cr, SUPERUSER_ID, {})
    env['res.company'].search([]).write({
        'country_id': env.ref('base.ar').id,
    })

def post_init_hook(cr, registry):
    _logger.info('Post init hook initialized')
    update_companies_country(cr, registry)
