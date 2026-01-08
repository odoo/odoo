# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import fields, models
from odoo.tools import populate

CP_WEIGHTS = {1: 35, 2: 30, 3: 25, 4: 10}
_logger = logging.getLogger(__name__)

class Message(models.Model):
    _inherit = 'mail.message'

    @property
    def _populate_dependencies(self):
        return super()._populate_dependencies + ["res.users", "forum.post"]

    def _populate(self, size):
        """Randomly assign messages to some populated posts and answers.
        This makes sure these questions and answers get one to four comments.
        Also define a date that is more recent than the post/answer's create_date
        """
        records = super()._populate(size)
        comment_subtype = self.env.ref('mail.mt_comment')
        hours = [_ for _ in range(1, 24)]
        random = populate.Random('comments_on_forum_posts')
        users = self.env["res.users"].browse(self.env.registry.populated_models['res.users'])
        vals_list = []
        question_ids = self.env.registry.populated_models['forum.post']
        posts = self.env['forum.post'].search(['|', ('id', 'in', question_ids), ('parent_id', 'in', question_ids)])
        for post in random.sample(posts, int(len(question_ids) * 0.7)):
            nb_comments = random.choices(*zip(*CP_WEIGHTS.items()))[0]
            for counter in range(nb_comments):
                vals_list.append({
                    "author_id": random.choice(users.partner_id.ids),
                    "body": f"message_body_{counter}",
                    "date": fields.Datetime.add(post.create_date, hours=random.choice(hours)),
                    "message_type": "comment",
                    "model": "forum.post",
                    "res_id": post.id,
                    "subtype_id": comment_subtype.id,
                })
        messages = self.env["mail.message"].create(vals_list)
        _logger.info('mail.message: update comments create date and uid')
        _logger.info('forum.post: update last_activity_date for posts with comments and/or commented answers')
        query = """
            WITH comment_author AS(
                SELECT mm.id, mm.author_id, ru.id as user_id, ru.partner_id
                  FROM mail_message mm
                  JOIN res_users ru
                    ON mm.author_id = ru.partner_id
                 WHERE mm.id in %(comment_ids)s
            ),
            updated_comments as (
                UPDATE mail_message mm
                   SET create_date = date,
                       create_uid = ca.user_id
                  FROM comment_author ca
                 WHERE mm.id = ca.id
             RETURNING res_id as post_id, create_date as comment_date
            ),
            max_comment_dates AS (
                SELECT post_id, max(comment_date) as last_comment_date
                  FROM updated_comments
              GROUP BY post_id
            ),
            updated_posts AS (
                UPDATE forum_post fp
                   SET last_activity_date = CASE  --on questions, answer could be more recent
                  WHEN fp.parent_id IS NOT NULL THEN greatest(last_activity_date, last_comment_date)
                  ELSE last_comment_date END
                  FROM max_comment_dates
                 WHERE max_comment_dates.post_id = fp.id
             RETURNING fp.id as post_id, fp.last_activity_date as last_activity_date, fp.parent_id as parent_id
            )
            UPDATE forum_post fp
               SET last_activity_date = greatest(fp.last_activity_date, up.last_activity_date)
              FROM updated_posts up
             WHERE up.parent_id = fp.id
    """
        self.env.cr.execute(query, {'comment_ids': tuple(messages.ids)})
        return records + messages
