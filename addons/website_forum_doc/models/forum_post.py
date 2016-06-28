# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Post(models.Model):
    _inherit = 'forum.post'

    documentation_toc_id = fields.Many2one('forum.documentation.toc', string='Documentation ToC', ondelete='set null')
    documentation_stage_id = fields.Many2one('forum.documentation.stage', string='Documentation Stage',
                                             default=lambda self: self.env['forum.documentation.stage'].search([], limit=1))
    color = fields.Integer(string='Color Index')

    @api.multi
    def _read_group_stage_ids(self, domain, read_group_order=None, access_rights_uid=None):
        return self.env['forum.documentation.stage'].search([]).name_get(), {}

    _group_by_full = {
        'documentation_stage_id': _read_group_stage_ids,
    }
