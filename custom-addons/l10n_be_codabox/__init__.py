from . import models

from odoo.tools.translate import _lt
from odoo.exceptions import UserError


def _l10n_be_codabox_pre_init_hook(env):
    companies = env['res.company'].search([
        ('partner_id.country_id.code', '=', 'BE'),
        ('vat', '!=', False),
    ])
    # The field is defined in account_reports module which this module does not depend on in 17.0
    if "account_representative_id" in env['res.company']._fields:
        # If we are in a demo db, create a demo accounting firm.
        if bool(env['ir.module.module'].search_count([('demo', '=', True)])) and all(not company.account_representative_id.vat for company in companies):
            accounting_firm = env['res.partner'].create({
                'name': 'Demo Accounting Firm',
                'vat': 'BE0428759497',
                'country_id': env.ref('base.be').id,
            })
            companies.write({
                'account_representative_id': accounting_firm.id,
            })
        companies = companies.filtered(lambda c: c.account_representative_id.vat)
    if not companies:
        raise UserError(_lt("The CodaBox module must be installed and configured by an Accounting Firm."))
