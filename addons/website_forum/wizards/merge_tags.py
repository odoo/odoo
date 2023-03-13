# -*- coding: utf-8 -*-
from nltk.stem import WordNetLemmatizer
from odoo import models, api, fields

class MergeTagsWizard(models.TransientModel):

    _name = 'forum.tag.merge_tags'
    _description = 'Merge Tag Wizard'

    def generate_line_ids(self):
        self.ensure_one()
        tag_ids = self.env['forum.tag'].search([])

        tags_by_lemma = {}
        for tag in tag_ids:
            name = tag.name
            lemma = WordNetLemmatizer().lemmatize(name, pos="v")
            if lemma not in tags_by_lemma:
                tags_by_lemma[lemma] = tag
            else:
                tags_by_lemma[lemma] += tag

        lines = self.env['forum.tag.merge_tags_line'].search([])
        lines.unlink()

        for lemma, tags in tags_by_lemma.items():
            if len(tags) > 1:    #if there is 2 ord more tags for the same lemma
                self.env['forum.tag.merge_tags_line'].create({
                    'name':lemma,
                    'tag_ids':[(6, 0, tags.ids)],
                })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Merge Tags',
            'view_mode': 'tree',
            'view_id': self.env.ref('website_forum.merge_tags_lines_view').id,
            'res_model': 'forum.tag.merge_tags_line',
            'target': 'current',
        }


class MergeTagsLine(models.TransientModel):
    _name = 'forum.tag.merge_tags_line'
    _description = 'Merge Tag Line'

    @api.depends('tag_ids')
    def _default_get_master(self):
        for record in self:
            record.master_id = record.tag_ids[0]
            for tag in record.tag_ids:
                if tag.name == record.name:
                    record.master_id = tag

    name = fields.Char(string="Base Name")
    tag_ids = fields.Many2many('forum.tag')
    master_id = fields.Many2one('forum.tag', compute='_default_get_master')

    @api.multi
    def merge_ligne(self):
        self.ensure_one()
        posts_to_write = self.env["forum.post"]
        for tag in self.tag_ids:
            if tag != self.master_id:
                posts = self.env["forum.post"].search([('tag_ids', 'in', tag.id)])
                posts_to_write |= posts
                tag.unlink()
        posts_to_write.write({'tag_ids': [(4, self.master_id.id)]})
        self.unlink()


class MergeTagsManuallyWizard(models.TransientModel):
    _name = 'forum.tag.merge_tags_manually'
    _description = 'Merge Tag Manually Wizard'

    @api.depends('tag_ids')
    def _default_get_master(self):
        for record in self:
            return record.tag_ids[0]

    master_id = fields.Many2one('forum.tag', default=_default_get_master)
    tag_ids = fields.Many2many('forum.tag', default=lambda self: self._context.get('active_ids'))


    @api.multi
    def merge(self):
        self.ensure_one()
        posts_to_write = self.env["forum.post"]
        for tag in self.tag_ids:
            if tag != self.master_id:
                posts = self.env["forum.post"].search([('tag_ids', 'in', tag.id)])
                posts_to_write |= posts
                tag.unlink()
        posts_to_write.write({'tag_ids': [(4, self.master_id.id)]})
