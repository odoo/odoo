
from odoo import fields
from odoo.addons.website_slides.tests import common as slides_common
from odoo.tests.common import users

from freezegun import freeze_time


class TestPortalRating(slides_common.SlidesCase):

    @users('user_officer')
    def test_portal_rating(self):
        self.channel._action_add_members(self.user_portal.partner_id)
        rating = self.channel.with_user(self.user_portal).message_post(
            body='Love the course, would benefit from more videos though.',
            rating_value=5,
        ).rating_id

        rating = rating.with_env(self.env)

        with freeze_time('2025-05-01'):
            rating.write({'publisher_comment': 'Thank you, we will loo into it!'})

        # rating metadata is set to publisher / date
        self.assertEqual(rating.publisher_id, self.user_officer.partner_id)
        self.assertEqual(
            rating.publisher_datetime,
            fields.Datetime.from_string('2025-05-01 00:00:00')
        )

        # manager fixes typo
        with freeze_time('2025-05-02'):
            rating.with_user(self.user_manager).write({
                'publisher_comment': 'Thank you, we will look into it!'
            })

        # rating metadata is not modified, only content is
        self.assertEqual(rating.publisher_id, self.user_officer.partner_id)
        self.assertEqual(
            rating.publisher_datetime,
            fields.Datetime.from_string('2025-05-01 00:00:00')
        )
