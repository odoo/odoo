# -*- coding: utf-8 -*-

from markupsafe import Markup, escape
from odoo import Command, fields, models, _


class WorkflowActionRuleTask(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(selection_add=[('project.task', "Task")])

    def create_record(self, documents=None):
        rv = super(WorkflowActionRuleTask, self).create_record(documents=documents)
        if self.create_model == 'project.task':
            project = documents.folder_id._get_project_from_closest_ancestor() if len(documents.folder_id) == 1 else self.env['project.project']
            new_obj = self.env[self.create_model].create({
                'name': " / ".join(documents.mapped('name')) or _("New task from Documents"),
                'user_ids': [Command.set(self.env.user.ids)],
                'partner_id': documents.partner_id.id if len(documents.partner_id) == 1 else False,
                'project_id': project.id,
            })
            task_action = {
                'type': 'ir.actions.act_window',
                'res_model': self.create_model,
                'res_id': new_obj.id,
                'name': _("new %s from %s", self.create_model, new_obj.name),
                'view_mode': 'form',
                'views': [(False, "form")],
                'context': self._context,
            }
            if len(documents) == 1:
                document_msg = _('Task created from document %s', documents._get_html_link())
            else:
                document_msg = escape(_('Task created from documents'))
                document_msg += Markup("<ul>%s</ul>") % Markup().join(
                    Markup("<li>%s</li>") % document._get_html_link()
                    for document in documents)

            for document in documents:
                this_document = document
                if (document.res_model or document.res_id) and document.res_model != 'documents.document'\
                    and not (project and document.res_model == 'project.project' and document.res_id == project.id):
                    this_document = document.copy()
                    attachment_id_copy = document.attachment_id.with_context(no_document=True).copy()
                    this_document.write({'attachment_id': attachment_id_copy.id})

                # the 'no_document' key in the context indicates that this ir_attachment has already a
                # documents.document and a new document shouldn't be automatically generated.
                this_document.attachment_id.with_context(no_document=True).write({
                    'res_model': self.create_model,
                    'res_id': new_obj.id
                })
            new_obj.message_post(body=document_msg)
            return task_action
        return rv
