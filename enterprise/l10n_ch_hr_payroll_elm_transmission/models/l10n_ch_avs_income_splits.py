# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nChAvsIncomeSplits(models.Model):
    _name = 'l10n.ch.avs.splits'
    _description = 'Negative AVS Salary Splitting'
    _order = "year desc"
    _rec_name = 'employee_id'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "CH":
            raise UserError(_('You must be logged in a Swiss company to use this feature'))
        return super().default_get(field_list)

    employee_id = fields.Many2one("hr.employee", required=True)
    state = fields.Selection([("draft", "Draft"),
                              ("confirmed", "Confirmed")], default="draft")
    year = fields.Integer(default=lambda self: fields.Date.context_today(self).year)
    income_to_split = fields.Float(readonly=True)
    additional_delivery_date = fields.Date(help="Date of manual announcement when a split is not possible")
    avs_split_lines = fields.One2many("l10n.ch.avs.split.lines", "avs_split_id")

    def action_confirm(self):
        self.write({
            "state": "confirmed"
        })

    def action_cancel(self):
        self.write({
            "state": "draft"
        })


class L10nChAvsIncomeSplitLines(models.Model):
    _name = 'l10n.ch.avs.split.lines'
    _description = 'AVS Income Split Lines'

    avs_split_id = fields.Many2one("l10n.ch.avs.splits")

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    income = fields.Float(required=True)
