# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import purchase_stock, stock_account


class ResCompany(stock_account.ResCompany, purchase_stock.ResCompany):

    lc_journal_id = fields.Many2one('account.journal')
