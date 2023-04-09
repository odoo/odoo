# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo import api, fields, models


class EventTagCategory(models.Model):
    _name = 'event.tag.category'
    _inherit = ['event.tag.category', 'website.published.mixin']

    def _default_is_published(self):
        return True

    event_event = fields.Many2many('event.event')
    website_show = fields.Many2one(comodel_name='website', string='website_show', compute='_compute_website_id')
    website_id = fields.Many2many(comodel_name='website', string='website_id', compute='_compute_website_id', store=True)

    @api.depends('event_event.tag_ids', 'event_event.website_id') #
    def _compute_website_id(self):
        for record in self:
            websites = set()
            tags = self.env['event.tag'].search([('category_id', '=', record.id)])
            for tag in tags:
                recordset = self.env['event.event'].search([('tag_ids', '=', tag.id)]).website_id                
                websites = websites.union(set(recordset.mapped('id')))

            id = None if len(websites) == 0 or len(websites) > 1 else next(iter(websites))
            record.website_show = id
            record['website_id'] = list(set(record['website_id'].ids).union(websites))