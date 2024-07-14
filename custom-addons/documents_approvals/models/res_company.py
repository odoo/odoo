# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_approvals_settings = fields.Boolean(default=False)
    approvals_folder_id = fields.Many2one('documents.folder', string="Approvals Workspace",
                                          default=lambda self: self.env.ref('documents_approvals.documents_approvals_folder', raise_if_not_found=False),
                                          check_company=True)
    approvals_tag_ids = fields.Many2many('documents.tag', 'approvals_tags_rel')
