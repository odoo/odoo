# -*- coding: utf-8 -*-
from odoo import models, fields


class Batch_new(models.Model):
    _name = 'school.batch.new'
    _inherits = {'school.batch': 'batch_id'}

    batch_id = fields.Many2one(comodel_name='school.batch', string='Journal Entry')
    max_course = fields.Integer('Maximum course', default=1)