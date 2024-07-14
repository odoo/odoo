# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WorkflowTagAction(models.Model):
    _name = "documents.workflow.action"
    _description = "Document Workflow Tag Action"

    workflow_rule_id = fields.Many2one('documents.workflow.rule', ondelete='cascade')

    action = fields.Selection([
        ('add', "Add"),
        ('replace', "Replace by"),
        ('remove', "Remove"),
    ], default='add', required=True)

    facet_id = fields.Many2one('documents.facet', string="Category")
    tag_id = fields.Many2one('documents.tag', string="Tag")

    def execute_tag_action(self, document):
        if self.action == 'add' and self.tag_id.id:
            return document.write({'tag_ids': [(4, self.tag_id.id, False)]})
        elif self.action == 'replace' and self.facet_id.id:
            faceted_tags = self.env['documents.tag'].search([('facet_id', '=', self.facet_id.id)])
            if faceted_tags.ids:
                for tag in faceted_tags:
                    document.write({'tag_ids': [(3, tag.id, False)]})
            if self.tag_id:
                return document.write({'tag_ids': [(4, self.tag_id.id, False)]})
        elif self.action == 'remove':
            if self.tag_id.id:
                return document.write({'tag_ids': [(3, self.tag_id.id, False)]})
            elif self.facet_id:
                faceted_tags = self.env['documents.tag'].search([('facet_id', '=', self.facet_id.id)])
                for tag in faceted_tags:
                    return document.write({'tag_ids': [(3, tag.id, False)]})
