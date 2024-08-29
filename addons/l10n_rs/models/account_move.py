# -*- coding: utf-8 -*-
from odoo.addons import account
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountMove(models.Model, account.AccountMove):

    l10n_rs_turnover_date = fields.Date(string='Turnover Date')
