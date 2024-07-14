# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class Partner(models.Model):
    _inherit = "res.partner"

    document_count = fields.Integer('Document Count', compute='_compute_document_count')

    def _compute_document_count(self):
        read_group_var = self.env['documents.document']._read_group(
            [('partner_id', 'in', self.ids)],
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
