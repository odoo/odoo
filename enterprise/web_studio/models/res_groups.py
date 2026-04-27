# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Groups(models.Model):
    _name = 'res.groups'
    _inherit = ['studio.mixin', 'res.groups']
