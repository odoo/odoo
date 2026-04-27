from odoo.addons.social_instagram.tests.common import SocialInstagramCommon


class SocialInstagramCase(SocialInstagramCommon):

    def setUp(self):
        super().setUp()
        # default to single account to simplify basic tests
        self.social_post.account_ids = self.social_account

    def test_post_instagram_success_immediate(self):
        """ Test immediate success: FINISHED status on first check. """
        self.social_post.image_ids = self.social_post.image_ids[0]
        self.assertEqual(self.social_post.state, 'draft')

        with self.mock_instagram_api(status='FINISHED', media_id='ig_media_id_1'):
            self.social_post._action_post()

        self.assertEqual(self.social_post.state, 'posted')
        live_post = self.social_post.live_post_ids
        self.assertEqual(len(live_post), 1)
        self.assertEqual(live_post.state, 'posted')
        self.assertEqual(live_post.instagram_post_id, 'ig_media_id_1')

    def test_post_instagram_async_flow(self):
        """ Test async flow: IN_PROGRESS then FINISHED. """
        self.social_post.image_ids = self.social_post.image_ids[0]
        self.assertEqual(self.social_post.state, 'draft')

        with self.mock_instagram_api(status='IN_PROGRESS', media_id='ig_media_id_async'):
            with self.capture_triggers('social.ir_cron_post_scheduled') as triggers:
                self.social_post._action_post()

            live_post = self.social_post.live_post_ids
            self.assertEqual(len(live_post), 1)
            self.assertEqual(live_post.state, 'posting')
            self.assertEqual(self.social_post.state, 'posting')
            self.assertEqual(len(triggers.records), 1)
            self.assertEqual(live_post.instagram_post_id, 'containerID-ig_media_id_async_0')

        with self.mock_instagram_api(status='FINISHED', media_id='ig_media_id_async'):
            live_post._post_instagram()

        self.assertEqual(self.social_post.state, 'posted')
        self.assertEqual(live_post.state, 'posted')
        self.assertEqual(live_post.instagram_post_id, 'ig_media_id_async')

    def test_post_instagram_published_status(self):
        """ Defensive test for the PUBLISHED status.
        This can happen if a previous cron retry successfully published the container but the response was lost
        before we could write state=posted, leaving the record stuck in 'posting'.
        On the next retry we find it already PUBLISHED and treat it as a success.
        """
        self.social_post.image_ids = self.social_post.image_ids[0]
        with self.mock_instagram_api(status='IN_PROGRESS', media_id='ig_media_id_pub'):
            self.social_post._action_post()
            live_post = self.social_post.live_post_ids
            self.assertEqual(len(live_post), 1)
            self.assertEqual(live_post.state, 'posting')

        with self.mock_instagram_api(status='PUBLISHED', media_id='ig_media_id_pub'):
            live_post._post_instagram()

        self.assertEqual(self.social_post.state, 'posted')
        self.assertEqual(live_post.state, 'posted')
        self.assertEqual(live_post.instagram_post_id, 'ig_media_id_pub')

    def test_post_instagram_carousel_async_flow(self):
        """ Test carousel async flow: items FINISHED then carousel container IN_PROGRESS. """
        self.assertEqual(self.social_post.state, 'draft')
        self.assertEqual(len(self.social_post.image_ids), 2)

        with self.mock_instagram_api(status='IN_PROGRESS', media_id='ig_carousel_id'):
            with self.capture_triggers('social.ir_cron_post_scheduled') as triggers:
                self.social_post._action_post()

            live_post = self.social_post.live_post_ids
            self.assertEqual(len(live_post), 1)
            self.assertEqual(live_post.state, 'posting')
            self.assertEqual(len(triggers.records), 1)
            self.assertEqual(live_post.instagram_post_id, 'containerID-ig_carousel_id_2')

        with self.mock_instagram_api(status='FINISHED', media_id='ig_carousel_id'):
            live_post._post_instagram()

        self.assertEqual(self.social_post.state, 'posted')
        self.assertEqual(live_post.state, 'posted')
        self.assertEqual(live_post.instagram_post_id, 'ig_carousel_id')

    def test_post_instagram_error_status(self):
        """ Test behavior when the container status is 'ERROR'. """
        self.social_post.image_ids = self.social_post.image_ids[0]
        with self.mock_instagram_api(status='IN_PROGRESS', media_id='ig_media_id_err'):
            self.social_post._action_post()
            live_post = self.social_post.live_post_ids
            self.assertEqual(len(live_post), 1)
            self.assertEqual(live_post.state, 'posting')

        with self.mock_instagram_api(status='ERROR', media_id='ig_media_id_err'):
            live_post._post_instagram()

        self.assertEqual(self.social_post.state, 'posted')
        self.assertEqual(live_post.state, 'failed')
        self.assertTrue(live_post.failure_reason)
