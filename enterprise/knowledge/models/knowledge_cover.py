# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Cover(models.Model):
    _name = "knowledge.cover"
    _description = "Knowledge Cover"

    attachment_id = fields.Many2one("ir.attachment", string="Cover attachment", required=True, ondelete="cascade")
    article_ids = fields.One2many("knowledge.article", "cover_image_id", string="Articles using cover")
    attachment_url = fields.Char("Cover URL", compute="_compute_attachment_url", store=True)

    @api.depends('attachment_id')
    def _compute_attachment_url(self):
        # Add an url for frontend access.
        for cover in self:
            if cover.attachment_id.url:
                cover.attachment_url = cover.attachment_id.url
            else:
                access_token = cover.attachment_id.generate_access_token()[0]
                cover.attachment_url = "/web/image/%s?access_token=%s" % (cover.attachment_id.id, access_token)

    @api.model_create_multi
    def create(self, vals_list):
        """ Create the covers, then link the attachments used to the created
        records, because when uploading a new cover, the attachment is uploaded
        with res_id=0, then the cover is created using the uploaded attachment.
        """
        if any(len(vals) == 1 and 'name' in vals for vals in vals_list):
            raise UserError(_('You cannot create a new Knowledge Cover from here.'))
        covers = super().create(vals_list)

        for cover in covers.filtered(lambda cover: not cover.attachment_id.res_id):
            cover.attachment_id.write({'res_model': 'knowledge.cover', 'res_id': cover.id, })

        return covers

    @api.autovacuum
    def _gc_unused_covers(self):
        return self.with_context(active_test=False).search([('article_ids', '=', False)]).unlink()
