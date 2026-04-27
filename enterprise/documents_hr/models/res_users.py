# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    document_ids = fields.One2many('documents.document', compute='_compute_documents')
    document_count = fields.Integer('Documents', compute='_compute_documents')

    @api.depends('partner_id')
    def _compute_documents(self):
        documents_read_group = dict(self.env['documents.document']._read_group(
            ['&', ('partner_id', 'in', self.env.user.partner_id.ids), '|', ('owner_id', '=', self.env.user.id), ('access_ids.partner_id', 'in', self.env.user.partner_id.ids)],
            ['partner_id'],
            ['id:array_agg'],
        ))
        for user in self:
            document_ids = self.env['documents.document'].browse(documents_read_group.get(user.partner_id, []))
            user.document_ids = document_ids
            user.document_count = len(user.document_ids)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['document_count']

    def action_see_documents(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('documents.document_action')
        return action | {
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {
                "default_partner_id": self.partner_id.id,
                "searchpanel_default_folder_id": False
            },
        }
