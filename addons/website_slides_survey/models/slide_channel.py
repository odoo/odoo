# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Channel(models.Model):
    _inherit = 'slide.channel'

    nbr_certifications = fields.Integer("Number of Certifications", compute='_compute_slides_statistics', store=True)

    def _compute_slides_statistics_type(self, read_group_res):
        result = super(Channel, self)._compute_slides_statistics_type(read_group_res)
        for cid in result:
            result[cid]['nbr_certifications'] = 0
        for res_group in read_group_res:
            cid = res_group['channel_id'][0]
            result[cid]['nbr_certifications'] += res_group.get('slide_type', '') == 'certification' and res_group['__count'] or 0
        return result


class Category(models.Model):
    _inherit = 'slide.category'

    nbr_certifications = fields.Integer("Number of Certifications", compute='_count_presentations', store=True)

    def _extract_count_presentations_type(self, result, record_id):
        statistics = super(Category, self)._extract_count_presentations_type(result, record_id)
        statistics['nbr_certifications'] = result[record_id].get('certification', 0)
        statistics['total_slides'] += statistics['nbr_certifications']

        return statistics
