# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    documents_approvals_settings = fields.Boolean(related='company_id.documents_approvals_settings',
                                                  readonly=False, string="Approvals")
    approvals_folder_id = fields.Many2one('documents.folder', related='company_id.approvals_folder_id',
                                          readonly=False, string="Approvals default workspace")
    approvals_tag_ids = fields.Many2many('documents.tag', 'approvals_tags_rel',
                                         related='company_id.approvals_tag_ids',
                                         readonly=False, string="Approvals Tags")

    @api.onchange('approvals_folder_id')
    def onchange_approvals_folder(self):
        if self.approvals_folder_id != self.approvals_tag_ids.folder_id:
            self.approvals_tag_ids = False
