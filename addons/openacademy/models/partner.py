# -*- coding: utf-8 -*-
from odoo import models, fields, api

class Partner(models.Model):
    _inherit = 'res.partner'
    # Add a new column to the res.partner model, by default partners are not
    # instructors
    instructor = fields.Boolean("Instructor", default=False)
    session_ids = fields.Many2many('openacademy.session', string="Attended Sessions", readonly=True)
    level = fields.Integer(compute="_get_level", string="Teacher", store=True)

    @api.depends('category_id', 'category_id.name')
    def _get_level(self):
        for partner in self:
            levels = []
            for categ in partner.category_id:
                if "Teacher / Level" in categ.name:
                    levels.append(int(categ.name.split(' ')[-1]))

            partner.level = max(levels) if levels else 0
