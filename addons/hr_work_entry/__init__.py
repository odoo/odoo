# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import controllers


def post_init_hook(env):
    """Copy the generic time types for the countries of companies that existed before this
    module did."""
    companies = env['res.company'].search([])
    env['res.company']._copy_generic_work_entry_types(companies.country_id)
