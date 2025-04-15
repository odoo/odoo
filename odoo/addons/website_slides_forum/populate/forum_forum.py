# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import zip_longest

from odoo import models
from odoo.addons.website_slides.populate.slide_channel import SlideChannel


class SlidesForum(models.Model):
    _inherit = 'forum.forum'

    @property
    def _populate_sizes(self):
        return {size: count + SlideChannel._populate_sizes[size] for size, count in super()._populate_sizes.items()}

    @property
    def _populate_dependencies(self):
        return super()._populate_dependencies + ['slide.channel']

    def _populate_factories(self):
        def link_course(iterator, *args, **kwargs):
            courses = self.env['slide.channel'].browse(self.env.registry.populated_models['slide.channel'])
            for values, course in zip_longest(iterator, courses):
                if course:
                    values.update(slide_channel_ids=course, name=f"{course.name}'s Forum")
                yield values

        return super()._populate_factories() + [
            ('_name_and_course', link_course),
        ]
