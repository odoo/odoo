# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

def _set_tax_included_on_website_sale(env):
    # On the installation of the module, we want every brazilian companies' websites to have the show_line_subtotals_tax_selection set to 'tax_included'
    websites = env['website'].search([('company_id', '!=', 'False')])
    for website in websites:
        if website.company_id.country_id.code == 'BR':
            website.show_line_subtotals_tax_selection = 'tax_included'

def _l10n_br_website_sale_post_init_hook(env):
    _set_tax_included_on_website_sale(env)
