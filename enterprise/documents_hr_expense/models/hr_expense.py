# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrExpense(models.Model):
    _name = 'hr.expense'
    _inherit = ['hr.expense', 'documents.unlink.mixin']

    document_count = fields.Integer(string='Document Count', compute="_compute_document_count")

    def _compute_document_count(self):
        document_data = self.env['documents.document']._read_group([
            ('res_id', 'in', self.ids), ('res_model', '=', self._name)],
            groupby=['res_id'], aggregates=['__count'])
        mapped_data = dict(document_data)
        for expense in self:
            expense.document_count = mapped_data.get(expense.id, 0)

    def action_open_attachments(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('documents.document_action')
        action['domain'] = [('res_model', '=', self._name), ('res_id', '=', self.id)]
        return action
