# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    repair_ids = fields.One2many('repair.order', 'invoice_id', readonly=True, copy=False)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    repair_line_ids = fields.One2many('repair.line', 'invoice_line_id', readonly=True, copy=False)
    repair_fee_ids = fields.One2many('repair.fee', 'invoice_line_id', readonly=True, copy=False)
