# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fiscalyear_last_day = fields.Integer(related='company_id.fiscalyear_last_day', readonly=False)
    fiscalyear_last_month = fields.Selection(related='company_id.fiscalyear_last_month', readonly=False)
    period_lock_date = fields.Date(related='company_id.period_lock_date', readonly=False)
    fiscalyear_lock_date = fields.Date(related='company_id.fiscalyear_lock_date', readonly=False)
    group_fiscal_year = fields.Boolean(string='Fiscal Years', implied_group='om_fiscal_year.group_fiscal_year')
