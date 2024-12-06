# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventTagCategory(models.Model):
    _inherit = ['event.tag.category']

    show_on_resume = fields.Boolean("Show on Resume", help="Display events with this tag on employee resumes")
