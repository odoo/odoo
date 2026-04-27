# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.osv import expression


class Partner(models.Model):
    _inherit = "res.partner"

    document_count = fields.Integer('Document Count', compute='_compute_document_count')

    def _compute_document_count(self):
        read_group_var = self.env['documents.document']._read_group(
            expression.AND([
                [('partner_id', 'in', self.ids)],
                [('type', '!=', 'folder')],
            ]),
            groupby=['partner_id'],
            aggregates=['__count'])

        document_count_dict = {partner.id: count for partner, count in read_group_var}
        for record in self:
            record.document_count = document_count_dict.get(record.id, 0)

    def action_see_documents(self):
        self.ensure_one()
        return {
            'name': _('Documents'),
            'domain': [('partner_id', '=', self.id)],
            'res_model': 'documents.document',
            'type': 'ir.actions.act_window',
            'views': [(False, 'kanban')],
            'view_mode': 'kanban',
            'context': {
                "default_partner_id": self.id,
                "searchpanel_default_folder_id": False
            },
        }

    def action_create_members_to_invite(self):
        return {
            'res_model': 'res.partner',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('base.view_partner_simple_form').id,
            'view_mode': 'form',
        }
