# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _inherit = ['approval.request', 'documents.mixin']

    documents_count = fields.Integer(compute='_compute_documents_count')
    documents_enabled = fields.Boolean(related='company_id.documents_approvals_settings')

    def _get_document_vals_access_rights(self):
        """Make sure (only) request owner and approval users can view the document."""
        return {
            'access_via_link': 'view',
            'access_internal': 'none',
            'is_access_via_link_hidden': False,
        }

    def _get_document_owner(self):
        return self.env.user

    def _get_document_access_ids(self):
        return [(self.request_owner_id.partner_id, ('view', False))]

    def _get_document_tags(self):
        return self.company_id.approvals_tag_ids

    def _get_document_folder(self):
        return self.company_id.approvals_folder_id

    def _get_document_partner(self):
        return self.partner_id

    def _check_create_documents(self):
        return self.company_id.documents_approvals_settings and super()._check_create_documents()

    def _compute_documents_count(self):
        grouped_data = self.env['documents.document']._read_group(domain=[('res_model', '=', 'approval.request'),
                                                                          ('res_id', 'in', self.ids),
                                                                          ('active', '=', True)],
                                                                  groupby=['res_id'],
                                                                  aggregates=['__count'])
        mapped_data = dict(grouped_data)
        for record in self:
            record.documents_count = mapped_data.get(record.id, 0)

    def action_get_attachment_view(self):
        if not self.company_id.documents_approvals_settings:
            return super().action_get_attachment_view()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'documents.document',
            'name': _('Documents'),
            'view_mode': 'kanban,list,form',
            'domain': [
                '|',
                ('type', '=', 'folder'),
                '&',
                ('res_model', '=', 'approval.request'),
                ('res_id', 'in', self.ids),
            ],
            'context': {
                'searchpanel_default_folder_id': self._get_document_folder().id,
                'default_res_model': 'approval.request',
                'default_res_id': self.ids[0],
            },
        }
