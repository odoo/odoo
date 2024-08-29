# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import website_slides

from odoo import models
from odoo.tools import populate


class SlideChannel(models.Model, website_slides.SlideChannel):
    _populate_sizes = {'small': 2, 'medium': 8, 'large': 20}

    def _populate_factories(self):
        return [
            ('name', populate.constant('Course_{counter}')),
            ('description', populate.constant('This is course number {counter}')),
            ('website_published', populate.randomize([True, False], weights=[4, 1])),
        ]
