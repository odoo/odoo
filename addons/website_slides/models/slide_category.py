# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Category(models.Model):
    """ Channel contain various categories to manage its slides """
    _name = 'slide.category'
    _description = "Slides Category"
    _order = "sequence, id"

    name = fields.Char('Name', translate=True, required=True)
    channel_id = fields.Many2one('slide.channel', string="Channel", required=True, ondelete='cascade')
    sequence = fields.Integer(default=10, help='Display order')
    slide_ids = fields.One2many('slide.slide', 'category_id', string="Slides")
    nbr_presentation = fields.Integer("Number of Presentations", compute='_count_presentations', store=True)
    nbr_document = fields.Integer("Number of Documents", compute='_count_presentations', store=True)
    nbr_video = fields.Integer("Number of Videos", compute='_count_presentations', store=True)
    nbr_infographic = fields.Integer("Number of Infographics", compute='_count_presentations', store=True)
    nbr_webpage = fields.Integer("Number of Webpages", compute='_count_presentations', store=True)
    total_slides = fields.Integer(compute='_count_presentations', store=True, oldname='total')

    @api.depends('slide_ids.slide_type', 'slide_ids.is_published')
    def _count_presentations(self):
        result = dict.fromkeys(self.ids, dict())
        res = self.env['slide.slide'].read_group(
            [('is_published', '=', True), ('category_id', 'in', self.ids)],
            ['category_id', 'slide_type'], ['category_id', 'slide_type'],
            lazy=False)

        type_stats = self._compute_slides_statistics_type(res)
        for cid, cdata in type_stats.items():
            result[cid].update(cdata)

        for record in self:
            record.update(result[record.id])

    def _compute_slides_statistics_type(self, read_group_res):
        """ Compute statistics based on all existing slide types """
        slide_types = self.env['slide.slide']._fields['slide_type'].get_values(self.env)
        keys = ['nbr_%s' % slide_type for slide_type in slide_types]
        keys.append('total_slides')
        result = dict((cid, dict((key, 0) for key in keys)) for cid in self.ids)
        for res_group in read_group_res:
            cid = res_group['category_id'][0]
            for slide_type in slide_types:
                result[cid]['nbr_%s' % slide_type] += res_group.get('slide_type', '') == slide_type and res_group['__count'] or 0
                result[cid]['total_slides'] += res_group.get('slide_type', '') == slide_type and res_group['__count'] or 0
        return result
