# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger


@tagged('security')
class TestAccess(common.SlidesCase):

    @mute_logger('odoo.models')
    def test_access_channel_invite(self):
        """ Invite channels don't give visibility if not member """
        self.channel.write({'visibility': 'invite'})

        self.channel.sudo(self.user_publisher).read(['name'])
        self.channel.sudo(self.user_emp).read(['name'])
        self.channel.sudo(self.user_portal).read(['name'])
        self.channel.sudo(self.user_public).read(['name'])

        self.slide.sudo(self.user_publisher).read(['name'])

        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_portal).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_portal).read(['name'])

        # if member -> can read
        membership = self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': self.user_emp.partner_id.id,
        })
        self.channel.sudo(self.user_emp).read(['name'])
        self.slide.sudo(self.user_emp).read(['name'])

        # not member anymore -> cannot read
        membership.unlink()
        self.channel.sudo(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_emp).read(['name'])

    @mute_logger('odoo.models')
    def test_access_channel_public(self):
        """ Public channels don't give visibility if not member """
        self.channel.write({'visibility': 'public'})

        self.channel.sudo(self.user_publisher).read(['name'])
        self.channel.sudo(self.user_emp).read(['name'])
        self.channel.sudo(self.user_portal).read(['name'])
        self.channel.sudo(self.user_public).read(['name'])

        self.slide.sudo(self.user_publisher).read(['name'])

        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_portal).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_public).read(['name'])

    @mute_logger('odoo.models')
    def test_access_channel_publish(self):
        """ Unpublished channels and their content are visible only to website people """
        self.channel.write({'website_published': False, 'visibility': 'public'})

        # channel available only to website
        self.channel.sudo(self.user_publisher).read(['name'])
        with self.assertRaises(AccessError):
            self.channel.sudo(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.channel.sudo(self.user_portal).read(['name'])
        with self.assertRaises(AccessError):
            self.channel.sudo(self.user_public).read(['name'])

        # slide available only to website
        self.slide.sudo(self.user_publisher).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_portal).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_public).read(['name'])

        # even members cannot see unpublished content
        self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': self.user_emp.partner_id.id,
        })
        with self.assertRaises(AccessError):
            self.channel.sudo(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_emp).read(['name'])

        # publish channel but content unpublished (even if can be previewed) still unavailable
        self.channel.write({'website_published': True})
        self.slide.write({
            'is_preview': True,
            'website_published': False,
        })

        self.slide.sudo(self.user_publisher).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_emp).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_portal).read(['name'])
        with self.assertRaises(AccessError):
            self.slide.sudo(self.user_public).read(['name'])

    @mute_logger('odoo.models')
    def test_access_slide_preview(self):
        """ Slides with preview flag are always visible even to non members if published """
        self.channel.write({'visibility': 'invite'})
        self.slide.write({'is_preview': True})

        self.slide.sudo(self.user_publisher).read(['name'])
        self.slide.sudo(self.user_emp).read(['name'])
        self.slide.sudo(self.user_portal).read(['name'])
        self.slide.sudo(self.user_public).read(['name'])
