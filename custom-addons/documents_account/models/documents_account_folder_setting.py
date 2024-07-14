# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DocumentsFolderSetting(models.Model):
    _name = 'documents.account.folder.setting'
    _description = 'Journal and Folder settings'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company,
                                 ondelete='cascade')
    journal_id = fields.Many2one('account.journal', required=True)
    folder_id = fields.Many2one('documents.folder', string="Workspace", required=True)
    tag_ids = fields.Many2many('documents.tag', string="Tags")

    _sql_constraints = [
        ('journal_unique', 'unique (journal_id)', "A setting already exists for this journal"),
    ]
