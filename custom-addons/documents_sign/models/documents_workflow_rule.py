# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class WorkflowActionRuleSign(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(selection_add=[('sign.template.new', "Signature PDF Template"),
                                                   ('sign.template.direct', "PDF to Sign")])

    def _compute_limited_to_single_record(self):
        super(WorkflowActionRuleSign, self)._compute_limited_to_single_record()
        for record in self:
            if record.create_model == 'sign.template.direct':
                record.limited_to_single_record = True

    def create_record(self, documents=None):
        rv = super(WorkflowActionRuleSign, self).create_record(documents=documents)
        if self.create_model.startswith('sign.template'):
            new_obj = None
            create_values_list = []
            for document in documents:
                create_values = {
                    'attachment_id': document.attachment_id.id,
                    'favorited_ids': [(4, self.env.user.id)],
                }
                if self.folder_id:
                    create_values['folder_id'] = self.folder_id.id
                elif self.domain_folder_id:
                    create_values['folder_id'] = self.domain_folder_id.id
                if document.tag_ids:
                    create_values['documents_tag_ids'] = [(6, 0, document.tag_ids.ids)]
                create_values_list.append(create_values)

            templates = self.env['sign.template'].create(create_values_list)

            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'sign.template',
                'name': _("New templates"),
                'view_id': False,
                'view_mode': 'kanban',
                'views': [(False, "kanban"), (False, "form")],
                'domain': [('id', 'in', templates.ids)],
                'context': self._context,
            }

            if len(templates.ids) == 1:
                return templates.go_to_custom_template(sign_directly_without_mail=self.create_model == 'sign.template.direct')
            return action
        return rv
