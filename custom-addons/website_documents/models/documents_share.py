# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class DocumentShare(models.Model):
    _name = 'documents.share'
    _inherit = ['documents.share']

    website_id = fields.Many2one('website', ondelete='cascade', compute='_compute_website_id',
                                 readonly=False, store=True)

    @api.depends('website_id')
    def _compute_full_url(self):
        super()._compute_full_url()

    @api.depends('folder_id')
    def _compute_website_id(self):
        for share in self.filtered(lambda share: not share.website_id):
            share.website_id = share.folder_id.company_id.website_id or self.env.company.website_id
