# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import http
from odoo.addons.base.tests.test_mimetypes import PNG
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.website_slides.tests import common
from odoo.exceptions import AccessError
from odoo.tests import tagged, HttpCase
from odoo.tools import mute_logger


@tagged('security')
class TestAccess(common.SlidesCase):

    @mute_logger('odoo.models', 'odoo.addons.base.models.ir_rule')
    def test_access_channel_invite(self):
        """ Invite channels don't give enroll if not member """
        self.channel.write({'enroll': 'invite'})

        self.channel.with_user(self.user_officer).read(['name'])
        self.channel.with_user(self.user_manager).read(['name'])
        self.channel.with_user(self.user_emp).read(['name'])
        self.channel.with_user(self.user_portal).read(['name'])
        self.channel.with_user(self.user_public).read(['name'])

        self.slide.with_user(self.user_officer).read(['name'])
        self.slide.with_user(self.user_manager).read(['name'])

        with self.assertRaises(AccessError):
            self.slide.with_user(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.with_user(self.user_portal).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.with_user(self.user_portal).read(['name'])

        # if member -> can read
        membership = self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': self.user_emp.partner_id.id,
        })
        self.channel.with_user(self.user_emp).read(['name'])
        self.slide.with_user(self.user_emp).read(['name'])

        # not member anymore -> cannot read
        membership.unlink()
        self.channel.with_user(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.with_user(self.user_emp).read(['name'])

    @mute_logger('odoo.models', 'odoo.addons.base.models.ir_rule')
    def test_access_channel_public(self):
        """ Public channels don't give enroll if not member """
        self.channel.write({'enroll': 'public'})

        self.channel.with_user(self.user_officer).read(['name'])
        self.channel.with_user(self.user_manager).read(['name'])
        self.channel.with_user(self.user_emp).read(['name'])
        self.channel.with_user(self.user_portal).read(['name'])
        self.channel.with_user(self.user_public).read(['name'])

        self.slide.with_user(self.user_officer).read(['name'])
        self.slide.with_user(self.user_manager).read(['name'])

        with self.assertRaises(AccessError):
            self.slide.with_user(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.with_user(self.user_portal).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.with_user(self.user_public).read(['name'])

    @mute_logger('odoo.models', 'odoo.addons.base.models.ir_rule')
    def test_access_channel_publish(self):
        """ Unpublished channels and their content are visible only to eLearning people """
        self.channel.write({'is_published': False, 'enroll': 'public'})
        self.channel.flush_model()

        # channel available only to eLearning
        self.channel.invalidate_model(['name'])
        self.channel.with_user(self.user_officer).read(['name'])
        self.channel.invalidate_model(['name'])
        self.channel.with_user(self.user_manager).read(['name'])
        with self.assertRaises(AccessError):
            self.channel.invalidate_model(['name'])
            self.channel.with_user(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.channel.invalidate_model(['name'])
            self.channel.with_user(self.user_portal).read(['name'])
        with self.assertRaises(AccessError):
            self.channel.invalidate_model(['name'])
            self.channel.with_user(self.user_public).read(['name'])

        # slide available only to eLearning
        self.channel.invalidate_model(['name'])
        self.slide.with_user(self.user_officer).read(['name'])
        self.channel.invalidate_model(['name'])
        self.slide.with_user(self.user_manager).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.invalidate_model(['name'])
            self.slide.with_user(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.invalidate_model(['name'])
            self.slide.with_user(self.user_portal).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.invalidate_model(['name'])
            self.slide.with_user(self.user_public).read(['name'])

        # even members cannot see unpublished content
        self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': self.user_emp.partner_id.id,
        })
        with self.assertRaises(AccessError):
            self.channel.invalidate_model(['name'])
            self.channel.with_user(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.invalidate_model(['name'])
            self.slide.with_user(self.user_emp).read(['name'])

        # publish channel but content unpublished (even if can be previewed) still unavailable
        self.channel.write({'is_published': True})
        self.slide.write({
            'is_preview': True,
            'is_published': False,
        })
        self.channel.flush_model()
        self.slide.flush_model()

        self.slide.invalidate_model(['name'])
        self.slide.with_user(self.user_officer).read(['name'])
        self.slide.invalidate_model(['name'])
        self.slide.with_user(self.user_manager).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.invalidate_model(['name'])
            self.slide.with_user(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.invalidate_model(['name'])
            self.slide.with_user(self.user_portal).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.invalidate_model(['name'])
            self.slide.with_user(self.user_public).read(['name'])

    @mute_logger('odoo.models', 'odoo.addons.base.models.ir_rule')
    def test_access_slide_preview(self):
        """ Slides with preview flag are always visible even to non members if published """
        self.channel.write({'enroll': 'invite'})
        self.slide.write({'is_preview': True})
        self.slide.flush_model()

        self.slide.with_user(self.user_officer).read(['name'])
        self.slide.with_user(self.user_manager).read(['name'])
        self.slide.with_user(self.user_emp).read(['name'])
        self.slide.with_user(self.user_portal).read(['name'])
        self.slide.with_user(self.user_public).read(['name'])


class TestAccessHttp(common.SlidesCase, HttpCase):
    @mute_logger('odoo.models', 'odoo.addons.base.models.ir_rule', 'odoo.http')
    def test_access_slide_attachment(self):
        """Check the document of slides, pdf or images, stored in a binary field, so as `ir.attachment`,
        are accessible to a user according to his access to the slide itself"""
        image_placeholder = self.env['ir.binary']._placeholder()

        slides = self.env['slide.slide'].create([
            {
                'name': 'Foo',
                'channel_id': self.channel.id,
                'slide_category': 'infographic',
                'is_published': True,
                'binary_content': PNG,
                'is_preview': True,
            },
            {
                'name': 'Bar',
                'channel_id': self.channel.id,
                'slide_category': 'document',
                'is_published': True,
                'binary_content': base64.b64encode(b'bar'),
                'is_preview': True,
            },
        ])
        slide_image, slide_pdf = slides

        def can_read_slides_content(user, can_read):
            self.authenticate(user.login, user.login)

            # Image slide
            for url in [
                f'/slides/slide/{slide_image.id}/get_image?field=image_1024',
                f'/web/image/slide.slide/{slide_image.id}/image_1024',
                f'/web/content/slide.slide/{slide_image.id}/binary_content',
                f'/web/content/slide.slide/{slide_image.id}/image_binary_content',
            ]:
                response = self.url_open(url)
                if can_read:
                    self.assertEqual(
                        base64.b64encode(response.content),
                        PNG,
                        f'{user.login} must be able to see the slide image',
                    )
                else:
                    self.assertTrue(
                        response.status_code == 404 or response.content in (image_placeholder, b''),
                        f'{user.login} must not be able to see the slide image',
                    )

            # PDF Slide
            for url in [
                f'/slides/slide/{slide_pdf.id}/pdf_content',
                f'/web/content/slide.slide/{slide_pdf.id}/binary_content',
                f'/web/content/slide.slide/{slide_pdf.id}/document_binary_content',
            ]:
                response = self.url_open(url)
                if can_read:
                    self.assertEqual(
                        response.content,
                        b'bar',
                        f'{user.login} must be able to see the slide pdf',
                    )
                else:
                    self.assertIn(
                        response.status_code,
                        (403, 404),
                        f'{user.login} must not be able to see the slide pdf',
                    )

        for user, expected in [
            (self.user_public, True),
            (self.user_portal, True),
            (self.user_emp, True),
            (self.user_manager, True),
            (self.user_officer, True),
        ]:
            can_read_slides_content(user, expected)

        slides.is_preview = False

        for user, expected in [
            (self.user_public, False),
            (self.user_portal, False),
            (self.user_emp, False),
            (self.user_manager, True),
            (self.user_officer, True),
        ]:
            can_read_slides_content(user, expected)

        membership = self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': self.user_emp.partner_id.id,
        })
        can_read_slides_content(self.user_emp, True)
        membership.unlink()
        can_read_slides_content(self.user_emp, False)

        membership = self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': self.user_portal.partner_id.id,
        })
        can_read_slides_content(self.user_portal, True)
        membership.unlink()
        can_read_slides_content(self.user_portal, False)


@tagged('functional', 'security')
class TestRemoveMembership(common.SlidesCase):

    def setUp(self):
        super(TestRemoveMembership, self).setUp()
        self.channel_partner = self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': self.customer.id,
        })

        self.slide_partner = self.env['slide.slide.partner'].create({
            'slide_id': self.slide.id,
            'channel_id': self.channel.id,
            'partner_id': self.customer.id
        })

    def test_security_unlink(self):
        # Only the publisher can unlink channel_partner (and slide_partner by extension)
        with self.assertRaises(AccessError):
            self.channel_partner.with_user(self.user_public).unlink()
        with self.assertRaises(AccessError):
            self.channel_partner.with_user(self.user_portal).unlink()
        with self.assertRaises(AccessError):
            self.channel_partner.with_user(self.user_emp).unlink()

    def test_slide_partner_remove(self):
        id_slide_partner = self.slide_partner.id
        id_channel_partner = self.channel_partner.id
        self.channel_partner.with_user(self.user_officer).unlink()
        self.assertFalse(self.env['slide.channel.partner'].search([('id', '=', '%d' % id_channel_partner)]))
        # Slide(s) related to the channel and the partner is unlink too.
        self.assertFalse(self.env['slide.slide.partner'].search([('id', '=', '%d' % id_slide_partner)]))


@tagged('functional')
class TestAccessFeatures(common.SlidesCase):

    @mute_logger('odoo.models', 'odoo.addons.base.models.ir_rule')
    def test_channel_auto_subscription(self):
        user_employees = self.env['res.users'].search([('groups_id', 'in', self.ref('base.group_user'))])

        channel = self.env['slide.channel'].with_user(self.user_officer).create({
            'name': 'Test',
            'enroll': 'invite',
            'is_published': True,
            'enroll_group_ids': [(4, self.ref('base.group_user'))]
        })
        channel.invalidate_model(['partner_ids'])
        self.assertEqual(channel.partner_ids, user_employees.mapped('partner_id'))

        new_user = self.env['res.users'].create({
            'name': 'NewUser',
            'login': 'NewUser',
            'groups_id': [(6, 0, [self.ref('base.group_user')])]
        })
        channel.invalidate_model()
        self.assertEqual(channel.partner_ids, user_employees.mapped('partner_id') | new_user.partner_id)

        new_user_2 = self.env['res.users'].create({
            'name': 'NewUser2',
            'login': 'NewUser2',
            'groups_id': [(5, 0)]
        })
        channel.invalidate_model()
        self.assertEqual(channel.partner_ids, user_employees.mapped('partner_id') | new_user.partner_id)
        new_user_2.write({'groups_id': [(4, self.ref('base.group_user'))]})
        channel.invalidate_model()
        self.assertEqual(channel.partner_ids, user_employees.mapped('partner_id') | new_user.partner_id | new_user_2.partner_id)

        new_user_3 = self.env['res.users'].create({
            'name': 'NewUser3',
            'login': 'NewUser3',
            'groups_id': [(5, 0)]
        })
        channel.invalidate_model()
        self.assertEqual(channel.partner_ids, user_employees.mapped('partner_id') | new_user.partner_id | new_user_2.partner_id)
        self.env.ref('base.group_user').write({'users': [(4, new_user_3.id)]})
        channel.invalidate_model()
        self.assertEqual(channel.partner_ids, user_employees.mapped('partner_id') | new_user.partner_id | new_user_2.partner_id | new_user_3.partner_id)

    @mute_logger('odoo.models', 'odoo.addons.base.models.ir_rule')
    def test_channel_access_fields_employee(self):
        channel_manager = self.channel.with_user(self.user_manager)
        channel_emp = self.channel.with_user(self.user_emp)
        channel_portal = self.channel.with_user(self.user_portal)
        self.assertFalse(channel_emp.can_upload)
        self.assertFalse(channel_emp.can_publish)
        self.assertFalse(channel_portal.can_upload)
        self.assertFalse(channel_portal.can_publish)

        # allow employees to upload
        channel_manager.write({'upload_group_ids': [(4, self.ref('base.group_user'))]})
        self.assertTrue(channel_emp.can_upload)
        self.assertFalse(channel_emp.can_publish)
        self.assertFalse(channel_portal.can_upload)
        self.assertFalse(channel_portal.can_publish)

    @mute_logger('odoo.models', 'odoo.addons.base.models.ir_rule')
    def test_channel_access_fields_officer(self):
        self.assertEqual(self.channel.user_id, self.user_officer)

        channel_officer = self.channel.with_user(self.user_officer)
        self.assertTrue(channel_officer.can_upload)
        self.assertTrue(channel_officer.can_publish)

        channel_officer.write({'upload_group_ids': [(4, self.ref('base.group_system'))]})
        self.assertTrue(channel_officer.can_upload)
        self.assertTrue(channel_officer.can_publish)

        channel_manager = self.channel.with_user(self.user_manager)
        channel_manager.write({
            'upload_group_ids': [(5, 0)],
            'user_id': self.user_manager.id
        })
        self.assertFalse(channel_officer.can_upload)
        self.assertFalse(channel_officer.can_publish)
        self.assertTrue(channel_manager.can_upload)
        self.assertTrue(channel_manager.can_publish)

    @mute_logger('odoo.models', 'odoo.addons.base.models.ir_rule')
    def test_channel_access_fields_manager(self):
        channel_manager = self.channel.with_user(self.user_manager)
        self.assertTrue(channel_manager.can_upload)
        self.assertTrue(channel_manager.can_publish)

        # test upload group limitation: member of group_system OR responsible OR manager
        channel_manager.write({'upload_group_ids': [(4, self.ref('base.group_system'))]})
        self.assertFalse(channel_manager.can_upload)
        self.assertFalse(channel_manager.can_publish)
        channel_manager.write({'user_id': self.user_manager.id})
        self.assertTrue(channel_manager.can_upload)
        self.assertTrue(channel_manager.can_publish)

        # Needs the manager to write on channel as user_officer is not the responsible anymore
        channel_manager.write({'upload_group_ids': [(5, 0)]})
        self.assertTrue(channel_manager.can_upload)
        self.assertTrue(channel_manager.can_publish)
        channel_manager.write({'user_id': self.user_officer.id})
        self.assertTrue(channel_manager.can_upload)
        self.assertTrue(channel_manager.can_publish)

        # superuser should always be able to publish even if they are not the responsible
        channel_superuser = self.channel.sudo()
        channel_superuser.invalidate_recordset(['can_upload', 'can_publish'])
        self.assertTrue(channel_superuser.can_upload)
        self.assertTrue(channel_superuser.can_publish)

    @mute_logger('odoo.models.unlink', 'odoo.addons.base.models.ir_rule', 'odoo.addons.base.models.ir_model')
    def test_resource_access(self):
        resource_values = {
            'name': 'Image',
            'slide_id': self.slide_3.id,
            'resource_type': 'file',
            'data': base64.b64encode(b'Some content')
        }
        resource1, resource2 = self.env['slide.slide.resource'].with_user(self.user_officer).create(
            [resource_values for _ in range(2)])
        resource3 = self.env['slide.slide.resource'].with_user(self.user_officer).create([
            {'name': 'Link',
             'slide_id': self.slide_3.id,
             'resource_type': 'url',
             'link': 'https://www.odoo.com'}
        ])
        # No public access to resources
        with self.assertRaises(AccessError):
            resource1.with_user(self.user_public).read(['name'])
            resource3.with_user(self.user_public).read(['name'])

        with self.assertRaises(AccessError):
            resource1.with_user(self.user_public).write({'name': 'other name'})
            resource3.with_user(self.user_public).write({'name': 'other name'})

        # public access to knowing if there are resources, also by type
        self.assertTrue(self.slide_3.with_user(self.user_public)._has_additional_resources())
        self.assertTrue(self.slide_3.with_user(self.user_public)._has_additional_resources('file'))
        self.assertTrue(self.slide_3.with_user(self.user_public)._has_additional_resources('url'))

        # No random portal access
        with self.assertRaises(AccessError):
            resource1.with_user(self.user_portal).read(['name'])

        # Members can only read
        self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': self.user_portal.partner_id.id,
        })
        resource1.with_user(self.user_portal).read(['name'])
        with self.assertRaises(AccessError):
            resource1.with_user(self.user_portal).write({'name': 'other name'})

        # Other officers can only read
        user_officer_other = mail_new_test_user(
            self.env, name='Ornella Officer', login='user_officer_2', email='officer2@example.com',
            groups='base.group_user,website_slides.group_website_slides_officer'
        )
        resource1.with_user(user_officer_other).read(['name'])
        with self.assertRaises(AccessError):
            resource1.with_user(user_officer_other).write({'name': 'Another name'})

        with self.assertRaises(AccessError):
            self.env['slide.slide.resource'].with_user(user_officer_other).create(resource_values)
        with self.assertRaises(AccessError):
            resource1.with_user(user_officer_other).unlink()

        # Responsible officer can do anything on their own channels
        resource1.with_user(self.user_officer).write({'name': 'other name'})
        resource1.with_user(self.user_officer).unlink()

        # Managers can do anything on all channels
        resource2.with_user(self.user_manager).write({'name': 'Another name'})
        resource2.with_user(self.user_manager).unlink()
        self.env['slide.slide.resource'].with_user(self.user_manager).create(resource_values)


@tagged('functional')
class TestReview(common.SlidesCase, HttpCase):
    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_channel_multiple_reviews(self):
        self.authenticate("admin", "admin")

        res1 = self.opener.post(
            url='%s/mail/chatter_post' % self.base_url(),
            json={
                'params': {
                    'res_id': self.channel.id,
                    'res_model': 'slide.channel',
                    'message': 'My first review :)',
                    'rating_value': '2',
                    'pid': self.env.user.partner_id.id,
                    'csrf_token': http.Request.csrf_token(self),
                },
            },
        )
        self.assertIn("My first review :)", res1.text)


        res2 = self.opener.post(
            url='%s/mail/chatter_post' % self.base_url(),
            json={
                'params': {
                    'res_id': self.channel.id,
                    'res_model': 'slide.channel',
                    'message': 'My second review :)',
                    'rating_value': '2',
                    'pid': self.env.user.partner_id.id,
                    'csrf_token': http.Request.csrf_token(self),
                },
            },
        )
        self.assertIn("odoo.exceptions.ValidationError", res2.text)
