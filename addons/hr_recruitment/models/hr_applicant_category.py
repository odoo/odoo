# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import fields, models


class HrApplicantCategory(models.Model):
    _name = 'hr.applicant.category'
    _description = "Category of applicant"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char("Tag Name", required=True)
    color = fields.Integer(string='Color Index', default=_get_default_color)

    _name_uniq = models.Constraint(
        'unique (name)',
        'Tag name already exists!',
    )
