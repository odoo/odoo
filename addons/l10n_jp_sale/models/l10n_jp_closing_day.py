# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10n_JpClosingDay(models.Model):
    _name = 'l10n_jp.closing.day'
    _description = "Closing Day"
    _order = 'day'

    name = fields.Char(required=True, translate=True)
    day = fields.Integer(required=True, help="Day of the month. 31 stands for the end of the month.")
