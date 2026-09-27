from datetime import datetime
from freezegun import freeze_time

from odoo.addons.website_event.tests.common import TestEventOnlineCommon
from odoo.addons.website_event_track.controllers.location_display import EventTrackLocationDisplayController
from odoo.tests.common import HttpCase, users


class TestLocationDisplay(TestEventOnlineCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event_0.write({
            'is_published': True,
            'website_track': True,
        })
        cls.location = cls.env['event.track.location'].create({'name': 'Main Stage'})
        cls.tracks = cls.env['event.track'].create([
            {
                'name': 'Finished',
                'event_id': cls.event_0.id,
                'location_id': cls.location.id,
                'date': datetime(2026, 3, 5, 8),
                'duration': 1,
                'is_published': True,
            }, {
                'name': 'Live',
                'event_id': cls.event_0.id,
                'location_id': cls.location.id,
                'date': datetime(2026, 3, 5, 10),
                'duration': 1,
                'is_published': True,
                'partner_name': 'Test Speaker',
                'partner_function': 'Engineer',
                'partner_company_name': 'Example Company',
            }, {
                'name': 'Next',
                'event_id': cls.event_0.id,
                'location_id': cls.location.id,
                'date': datetime(2026, 3, 5, 12),
                'duration': 0.5,
                'is_published': True,
            }, {
                'name': 'Later',
                'event_id': cls.event_0.id,
                'location_id': cls.location.id,
                'date': datetime(2026, 3, 5, 13),
                'duration': 0.5,
                'is_published': True,
            }, {
                'name': 'Third upcoming track',
                'event_id': cls.event_0.id,
                'location_id': cls.location.id,
                'date': datetime(2026, 3, 5, 14),
                'duration': 0.5,
                'is_published': True,
            }, {
                'name': 'Fourth upcoming track',
                'event_id': cls.event_0.id,
                'location_id': cls.location.id,
                'date': datetime(2026, 3, 5, 14, 30),
                'duration': 0.5,
                'is_published': True,
            }, {
                'name': 'Unpublished',
                'event_id': cls.event_0.id,
                'location_id': cls.location.id,
                'date': datetime(2026, 3, 5, 10, 30),
                'duration': 0.5,
                'is_published': False,
            }, {
                'name': 'Tomorrow',
                'event_id': cls.event_0.id,
                'location_id': cls.location.id,
                'date': datetime(2026, 3, 6, 9),
                'duration': 1,
                'is_published': True,
            },
        ])
        cls.tomorrow_stage = cls.env['event.track.location'].create({'name': 'Tomorrow Stage'})
        cls.tomorrow_stage_track = cls.env['event.track'].create({
            'name': 'Tomorrow Elsewhere',
            'event_id': cls.event_0.id,
            'location_id': cls.tomorrow_stage.id,
            'date': datetime(2026, 3, 6, 10),
            'duration': 1,
            'is_published': True,
        })

    @users('user_eventmanager')
    def test_location_display_schedule(self):
        """ Test the location display schedule logic for live, upcoming, and finished tracks. """
        controller = EventTrackLocationDisplayController()
        event = self.event_0.with_env(self.env)
        location, tracks = self.location, self.tracks

        def get_schedule(location):
            return controller._get_location_display_schedule(
                event,
                location,
                controller._get_event_time_data(event),
            )

        self.assertEqual(event.location_display_upcoming_track_count, '3')
        with freeze_time(datetime(2026, 3, 5, 10, 15)):
            schedule = get_schedule(location)
        self.assertEqual(schedule['live_track'], tracks[1])
        self.assertEqual(schedule['live_status'], 'live')
        self.assertEqual(schedule['location_name'], location.name)
        self.assertEqual(schedule['upcoming_tracks'], tracks[2:5])

        event.location_display_upcoming_track_count = '4'
        with freeze_time(datetime(2026, 3, 5, 10, 15)):
            schedule = get_schedule(location)
        self.assertEqual(schedule['upcoming_tracks'], tracks[2:6])

        with freeze_time(datetime(2026, 3, 5, 11, 30)):
            gap_schedule = get_schedule(location)
        self.assertFalse(gap_schedule['live_track'])
        self.assertEqual(gap_schedule['live_status'], 'gap')

        with freeze_time(datetime(2026, 3, 5, 15)):
            finished_schedule = get_schedule(location)
        self.assertFalse(finished_schedule['upcoming_tracks'])
        self.assertEqual(finished_schedule['live_status'], 'finished')
        self.assertEqual(finished_schedule['next_track'], tracks[7])

        with freeze_time(datetime(2026, 3, 5, 10, 15)):
            tomorrow_schedule = get_schedule(self.tomorrow_stage)
        self.assertEqual(tomorrow_schedule['live_status'], 'none')
        self.assertEqual(tomorrow_schedule['next_track'], self.tomorrow_stage_track)

        with freeze_time(datetime(2026, 3, 7)):
            past_schedule = get_schedule(location)
        self.assertEqual(past_schedule['live_status'], 'none')
        self.assertEqual(past_schedule['location_name'], event.name)

        self.assertFalse(location.location_display_url)
        self.assertEqual(
            location.with_context(active_model='event.event', active_id=event.id).location_display_url,
            f'/event/{event.id}/location-display/{location.id}',
        )

    @freeze_time(datetime(2026, 3, 5, 10, 15))
    def test_location_display_page(self):
        """ Test the location display page content and background image display. """
        self.authenticate(None, None)
        live_track, next_track = self.tracks[1:3]
        display_url = self.location.with_context(
            active_model='event.event', active_id=self.event_0.id,
        ).location_display_url
        response = self.url_open(display_url)
        # Check the initial location display page content
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.location.name, response.text, "Location name should be displayed on the page.")
        self.assertIn(live_track.name, response.text, "Live track name should be displayed on the page.")
        self.assertIn('Test Speaker', response.text, "Speaker name should be displayed on the page.")
        self.assertIn(next_track.name, response.text, "Next track name should be displayed on the page.")
        self.assertIn(f'{display_url}/content', response.text, "Refresh content endpoint should be included in the page.")
        self.assertIn('o_wevent_location_display_refresh_status', response.text, "Refresh status should be included in the page.")
        self.assertNotIn('o_wevent_location_display_has_background', response.text, "Background image should not be displayed on the page.")
        # Check that the background image is displayed when set on the event
        self.event_0.location_display_background = (
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC'
        )
        response = self.url_open(display_url)
        background_image_url = (
            f'/web/image/event.event/{self.event_0.id}/location_display_background'
        )
        self.assertIn('o_wevent_location_display_has_background', response.text, "Background image should be displayed on the page.")
        self.assertIn(background_image_url, response.text, "Background image URL should be included in the page.")
        self.assertEqual(self.url_open(background_image_url).status_code, 200)
        # Check that the content endpoint returns the expected response
        content_response = self.url_open(f'{display_url}/content', json={'params': {}})
        self.assertEqual(content_response.status_code, 200)
        self.assertIn('o_wevent_location_display_content', content_response.json()['result'])
        self.assertIn(background_image_url, content_response.json()['result'])

        unrelated_location = self.env['event.track.location'].create({'name': 'Unrelated Stage'})
        unrelated_display_url = unrelated_location.with_context(
            active_model='event.event', active_id=self.event_0.id,
        ).location_display_url
        unrelated_response = self.url_open(unrelated_display_url)
        self.assertEqual(unrelated_response.status_code, 200)
        self.assertIn(self.event_0.name, unrelated_response.text)
        self.assertNotIn(unrelated_location.name, unrelated_response.text)

    def test_location_display_cookies_bar(self):
        """ Test that the location display page does not show the cookies bar even if it is enabled on the website. """
        self.authenticate(None, None)
        self.env.ref('base.default_website').cookies_bar = True
        self.assertIn('website_cookies_bar', self.url_open('/').text)
        display_url = self.location.with_context(
            active_model='event.event', active_id=self.event_0.id,
        ).location_display_url
        response = self.url_open(display_url)
        self.assertNotIn('website_cookies_bar', response.text)
