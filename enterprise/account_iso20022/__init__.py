# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def init_initiating_party_names(env):
    """ Sets the company name as the default value for the initiating
    party name on all existing companies once the module is installed. """
    for company in env['res.company'].search([]):
        company.iso20022_initiating_party_name = env['account.journal']._sepa_sanitize_communication(company.name)
