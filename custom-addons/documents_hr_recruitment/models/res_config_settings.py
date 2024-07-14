# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    documents_recruitment_settings = fields.Boolean(related='company_id.documents_recruitment_settings', readonly=False, string="Recruitment")
    recruitment_folder_id = fields.Many2one('documents.folder', related='company_id.recruitment_folder_id', readonly=False, string="Recruitment default workspace")
    recruitment_tag_ids = fields.Many2many('documents.tag', 'recruitment_tags_rel',
                                           related='company_id.recruitment_tag_ids',
                                           readonly=False, string="Recruitment Tags")

    @api.onchange('recruitment_folder_id')
    def onchange_recruitment_folder(self):
        if self.recruitment_folder_id != self.recruitment_tag_ids.mapped('folder_id'):
            self.recruitment_tag_ids = False
