# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    documents_approvals_settings = fields.Boolean(related='company_id.documents_approvals_settings',
                                                  readonly=False, string="Approvals")
    approvals_folder_id = fields.Many2one('documents.document', related='company_id.approvals_folder_id',
                                          readonly=False, string="Approvals default workspace")
    approvals_tag_ids = fields.Many2many('documents.tag', 'approvals_tags_rel',
                                         related='company_id.approvals_tag_ids',
                                         readonly=False, string="Approvals Tags")
