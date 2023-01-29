# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_rs_company_registry = fields.Char(string='Company ID', related='partner_id.l10n_rs_company_registry')
    l10n_rs_turnover_date = fields.Date(string='Turnover Date')
