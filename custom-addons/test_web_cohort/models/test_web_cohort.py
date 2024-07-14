# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WebCohortSimpleModel(models.Model):
    """ A very simple model with date_start, date_stop and measure. """

    _description = 'Simple Cohort Model'
    _name = 'web.cohort.simple.model'

    name = fields.Char()
    datetime_start = fields.Datetime()
    datetime_stop = fields.Datetime()
    date_start = fields.Date()
    date_stop = fields.Date()
    revenue = fields.Float()
    type_id = fields.Many2one("web.cohort.type")

class WebCohortType(models.Model):
    _description = 'Type for Cohort Model'
    _name = 'web.cohort.type'

    name = fields.Char()
