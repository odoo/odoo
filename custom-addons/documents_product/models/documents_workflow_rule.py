# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class WorkflowActionRuleProduct(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(selection_add=[('product.template', "Product template")])

    def create_record(self, documents=None):
        rv = super(WorkflowActionRuleProduct, self).create_record(documents=documents)
        if self.create_model == 'product.template':
            product = self.env[self.create_model].create({'name': 'product created from Documents'})
            image_is_set = False

            for document in documents:
                # this_document is the document in use for the workflow
                this_document = document
                if (document.res_model or document.res_id) and document.res_model != 'documents.document':
                    attachment_copy = document.attachment_id.with_context(no_document=True).copy()
                    this_document = document.copy({'attachment_id': attachment_copy.id})
                this_document.write({
                    'res_model': product._name,
                    'res_id': product.id,
                })
                if 'image' in this_document.mimetype and not image_is_set:
                    product.write({'image_1920': this_document.datas})
                    image_is_set = True

            view_id = product.get_formview_id()
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'product.template',
                'name': "New product template",
                'context': self._context,
                'view_mode': 'form',
                'views': [(view_id, "form")],
                'res_id': product.id if product else False,
                'view_id': view_id,
            }
        return rv
