# -*- coding: utf-8 -*-

from openerp.addons.website_portal.tests.common import TestWebsitePortalCommon


class TestWebsitePortalFlow(TestWebsitePortalCommon):

    def test_website_portal_followers(self):
        """ Test the flow of followers and notifications for portals. Intended
        flow :

         - people subscribe to a portal
         - when creating a new post, nobody except the creator follows it
         - people subscribed to the portal does not receive comments on posts
         - when published, a notification is sent to all portal followers
         - if someone subscribe to the post or comment it, it become follower
           and receive notification for future comments. """

        # Create a new portal, subscribe the employee to the portal
        test_portal = self.env['portal.portal'].sudo(self.user_portalmanager).create({
            'name': 'New Portal',
            'description': 'Presentation of new Odoo features'
        })
        self.assertIn(
            self.user_portalmanager.partner_id, test_portal.message_follower_ids,
            'website_portal: portal create should be in the portal followers')
        test_portal.message_subscribe([self.user_employee.partner_id.id, self.user_public.partner_id.id])

        # Create a new post, portal followers should not follow the post
        test_portal_post = self.env['portal.post'].sudo(self.user_portalmanager).create({
            'name': 'New Post',
            'portal_id': test_portal.id,
        })
        self.assertNotIn(
            self.user_employee.partner_id, test_portal_post.message_follower_ids,
            'website_portal: subscribing to a portal should not subscribe to its posts')
        self.assertNotIn(
            self.user_public.partner_id, test_portal_post.message_follower_ids,
            'website_portal: subscribing to a portal should not subscribe to its posts')

        # Publish the portal
        test_portal_post.write({'website_published': True})

        # Check publish message has been sent to portal followers
        publish_message = next((m for m in test_portal_post.portal_id.message_ids if m.subtype_id.id == self.ref('website_portal.mt_portal_portal_published')), None)
        self.assertEqual(
            set(publish_message.notified_partner_ids._ids),
            set([self.user_employee.partner_id.id, self.user_public.partner_id.id]),
            'website_portal: peuple following a portal should be notified of a published post')

        # Armand posts a message -> becomes follower
        test_portal_post.sudo().message_post(
            body='Armande PortalUser Commented',
            type='comment',
            author_id=self.user_employee.partner_id.id,
            subtype='mt_comment',
        )
        self.assertIn(
            self.user_employee.partner_id, test_portal_post.message_follower_ids,
            'website_portal: people commenting a post should follow it afterwards')
