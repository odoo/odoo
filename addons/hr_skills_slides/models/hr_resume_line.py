# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class HrResumeLine(models.Model):
    _inherit = 'hr.resume.line'

    channel_id = fields.Many2one('slide.channel', string="eLearning Course", readonly=True, index='btree_not_null')
    course_url = fields.Char(related='channel_id.website_absolute_url')
    duration = fields.Integer(string="Duration", compute='_compute_duration', readonly=False, store=True)

    @api.depends('channel_id')
    def _compute_duration(self):
        for resume_line in self:
            resume_line.duration = resume_line.channel_id.total_time

    @api.onchange('channel_id')
    def _onchange_channel_id(self):
        if not self.name and self.channel_id:
            self.name = self.channel_id.name
