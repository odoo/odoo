# -*- coding: utf-8 -*-
from odoo import fields, models


class WorkflowActionRuleApplicant(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(selection_add=[('hr.applicant', "Applicant")])

    def create_record(self, documents=None):
        rv = super(WorkflowActionRuleApplicant, self).create_record(documents=documents)
        if self.create_model == 'hr.applicant':
            applicants = self.env['hr.applicant']
            for document in documents:
                applicant = self.env['hr.applicant'].create({
                    'name': "New Application from Documents",
                    'user_id': False,
                })
                applicants |= applicant
                this_document = document
                if (document.res_model or document.res_id) and document.res_model != 'documents.document':
                    this_document = document.copy()
                    attachment_id_copy = document.attachment_id.with_context(no_document=True).copy()
                    this_document.write({'attachment_id': attachment_id_copy.id})

                this_document.attachment_id.with_context(no_document=True).write({
                    'res_model': 'hr.applicant',
                    'res_id': applicant.id
                })
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.applicant',
                'name': 'Applicant',
                'view_mode': 'tree,form',
                'views': [(False, "list"), (False, "form")],
                'domain': [('id', 'in', applicants.ids)],
                'context': self._context,
            }
            if len(applicants) == 1:
                action.update(
                    view_mode='form',
                    views=[(False, "form")],
                    res_id=applicants[0].id,
                )
            return action
        return rv
