# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'
    is_student = fields.Boolean(string='Is Student', default=False)

