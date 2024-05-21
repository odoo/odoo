# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models
from odoo.tools import populate

class Forum(models.Model):
    _inherit = 'forum.forum'
    _populate_sizes = {'small': 1, 'medium': 3, 'large': 10}

    def _populate_factories(self):

        def create_tags(values=None, random=None, **kwargs):
            """Attach a random number of tags to each forum."""
            return [
                Command.create({
                    'name': f"{values['name']}_tag_{i + 1}"
                }) for i in range(random.randint(1, 6))
            ]

        return [
            ('name', populate.constant('Forum_{counter}')),
            ('description', populate.constant('This is forum number {counter}')),
            ('tag_ids', populate.compute(create_tags)),
        ]
