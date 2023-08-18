# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate

CP_WEIGHTS = {1: 35, 2: 30, 3: 25, 4: 10}

class Message(models.Model):
    _inherit = 'mail.message'
    _populate_dependencies = ['forum.post']
    _populate_sizes = {'small': 100, 'medium': 1000, 'large': 90000}

    def _populate_factories(self):

        def get_res_id(iterator, *args):
            """Randomly assign messages to some populated posts and answers.
            This makes sure these questions and answers get one to four comments.
            """
            question_ids = self.env.registry.populated_models['forum.post']
            answers = self.env['forum.post'].search_read([('parent_id', 'in', question_ids)], ['id'])
            answer_ids = [answer_id for answer in answers for answer_id in answer.values()]
            sample_size = int(len(question_ids) * 0.7)
            res_ids = populate.random.sample(question_ids + answer_ids, sample_size)
            nb_comments = 0
            idx = 0
            post_to_comment_id = None

            for values in iterator:
                if nb_comments == 0:
                    nb_comments = populate.random.choices(*zip(*CP_WEIGHTS.items()))[0]
                    post_to_comment_id = res_ids[idx]
                    idx += 1
                nb_comments -= 1
                yield {**values, 'res_id': post_to_comment_id}

        return [
            ('body', populate.constant('message_body_{counter}')),
            ('message_type', populate.constant('comment')),
            ('model', populate.constant('forum.post')),
            ('res_id', get_res_id)
        ]
