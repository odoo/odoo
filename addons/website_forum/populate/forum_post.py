# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import populate

QA_WEIGHTS = {0: 25, 1: 35, 2: 20, 3: 10, 4: 4, 5: 3, 6: 2, 7: 1}

class Post(models.Model):
    _inherit = 'forum.post'
    # Include an additional average of 2 post answers for each given size
    # e.g.: 100 posts as populated_model_records = ~300 actual forum.posts records
    _populate_sizes = {'small': 100, 'medium': 1000, 'large': 90000}
    _populate_dependencies = ['forum.forum']

    def _populate_factories(self):
        forum_ids = self.env.registry.populated_models['forum.forum']

        def create_answers(values=None, random=None, **kwargs):
            return [fields.Command.create({
                    'name': f"reply to {values['name']}",
                    'forum_id': values['forum_id']})
                    for _ in range(random.choices(*zip(*QA_WEIGHTS.items()))[0])]

        return [
            ('name', populate.constant('post_{counter}')),
            ('forum_id', populate.randomize(forum_ids)),
            ('child_ids', populate.compute(create_answers)),
            ('last_activity_date', populate.randomize([
                fields.Datetime.now(),
                fields.Datetime.add(fields.Datetime.now(), hours=1)],
                [0.9, 0.1]))
        ]
