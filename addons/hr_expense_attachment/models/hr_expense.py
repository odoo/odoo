# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class HrExpense(models.Model):
    _inherit = "hr.expense"

    attachment_ids = fields.One2many("ir.attachment",string='Expense Attachments', compute="_compute_expense_attachments")

    def _compute_attachments(self):
        attachments = self.env["ir.attachment"]
        for record in self:
            record.attachment_ids = attachments.search([('res_model', '=', 'hr.expense'), ('res_id', '=', record.id)])
