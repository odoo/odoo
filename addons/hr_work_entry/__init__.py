# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import controllers


def post_init_hook(env):
    """Create the default time types of the non-localized countries of the companies that
    existed before this module did."""
    companies = env['res.company'].search([])
    env['res.company']._create_default_work_entry_types(companies.country_id)
