# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    document_ids = fields.One2many('documents.document', 'owner_id')
    document_count = fields.Integer('Documents', compute='_compute_document_count')

    @api.depends('document_ids')
    def _compute_document_count(self):
        for user in self:
            user.document_count = len(user.document_ids)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['document_count']

    def action_see_documents(self):
        self.ensure_one()
        return {
            'name': _('Documents'),
            'domain': [('owner_id', '=', self.id)],
            'res_model': 'documents.document',
            'type': 'ir.actions.act_window',
            'views': [(False, 'kanban'), (False, 'tree')],
            'view_mode': 'kanban,tree',
            'context': {
                "default_owner_id": self.id,
                "searchpanel_default_folder_id": False
            },
        }
