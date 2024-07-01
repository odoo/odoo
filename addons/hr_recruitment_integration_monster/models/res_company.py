# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    hr_recruitment_monster_username = fields.Char(string="Username")
    hr_recruitment_monster_password = fields.Char(string="Password")
