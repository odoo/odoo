# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Post(models.Model):
    _inherit = 'forum.post'

    documentation_toc_id = fields.Many2one('forum.documentation.toc', string='Documentation ToC',
                                           ondelete='set null', group_expand='_read_group_stage_ids')
    documentation_stage_id = fields.Many2one('forum.documentation.stage', string='Documentation Stage',
                                             default=lambda self: self.env['forum.documentation.stage'].search([], limit=1))
    color = fields.Integer(string='Color Index')

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return stages.search([], order=order)
