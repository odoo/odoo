# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import fields, models
from odoo.tools import populate

QA_WEIGHTS = {0: 25, 1: 35, 2: 20, 3: 10, 4: 4, 5: 3, 6: 2, 7: 1}
_logger = logging.getLogger(__name__)

class Post(models.Model):
    _inherit = 'forum.post'
    # Include an additional average of 2 post answers for each given size
    # e.g.: 100 posts as populated_model_records = ~300 actual forum.posts records
    _populate_sizes = {'small': 100, 'medium': 1000, 'large': 90000}
    _populate_dependencies = ['forum.forum', 'res.users']

    def _populate_factories(self):
        forum_ids = self.env.registry.populated_models['forum.forum']
        hours = [_ for _ in range(1, 49)]
        random = populate.Random('forum_posts')

        def create_answers(values=None, **kwargs):
            """Create random number of answers
            We set the `last_activity_date` to convert it to `create_date` in `_populate`
            as the ORM prevents setting these.
            """
            return [
                fields.Command.create({
                    'name': f"reply to {values['name']}",
                    'forum_id': values['forum_id'],
                    'content': 'Answer content',
                    'last_activity_date': fields.Datetime.add(values['last_activity_date'], hours=random.choice(hours)),
                })
                for _ in range(random.choices(*zip(*QA_WEIGHTS.items()))[0])
            ]

        def get_last_activity_date(iterator, *args):
            days = [_ for _ in range(3, 93)]
            now = fields.Datetime.now()

            for values in iterator:
                values.update(last_activity_date=fields.Datetime.subtract(now, days=random.choice(days)))
                yield values

        return [
            ('forum_id', populate.randomize(forum_ids)),
            ('name', populate.constant('post_{counter}')),
            ('last_activity_date', get_last_activity_date),  # Must be before call to 'create_answers'
            ('child_ids', populate.compute(create_answers)),
        ]

    def _populate(self, size):
        records = super()._populate(size)
        user_ids = self.env.registry.populated_models['res.users']

        # Overwrite auto-fields: use last_activity_date to update create date
        _logger.info('forum.post: update create date and uid')
        question_ids = tuple(records.ids)
        query = """
            SELECT setseed(0.5);
            UPDATE forum_post
               SET create_date = last_activity_date,
                   create_uid = floor(random() * (%(max_value)s - %(min_value)s + 1) + %(min_value)s)
             WHERE id in %(question_ids)s or parent_id in %(question_ids)s
        """
        self.env.cr.execute(query, {'question_ids': question_ids, 'min_value': user_ids[0], 'max_value': user_ids[-1]})

        _logger.info('forum.post: update last_activity_date of questions with answers')
        query = """
            WITH latest_answer AS(
                SELECT parent_id, max(last_activity_date) as answer_date
                  FROM forum_post
                 WHERE parent_id in %(question_ids)s
              GROUP BY parent_id
            )
            UPDATE forum_post fp
               SET last_activity_date = latest_answer.answer_date
              FROM latest_answer
             WHERE fp.id = latest_answer.parent_id
        """
        self.env.cr.execute(query, {'question_ids': question_ids})

        return records
