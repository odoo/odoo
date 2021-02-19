# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class ResGroups(models.Model):
    _inherit = "res.groups"

    _populate_sizes = {
        'small': 10,
        'medium': 100,
        'large': 1000,
    }

    def _populate_factories(self):

        return [
            ('name', populate.constant('Group_{counter}')),
        ]
