# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard


def _hr_holiday_post_init(env):
    french_companies = env['res.company'].search_count([('partner_id.country_id.code', '=', 'FR')])
    if french_companies:
        env['ir.module.module'].search([
            ('name', '=', 'l10n_fr_hr_work_entry_holidays'),
            ('state', '=', 'uninstalled')
        ]).sudo().button_install()

    env['resource.calendar.leaves'].load_public_holidays(companies=env.companies, convert_datetime=False)
