# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo.addons.website_slides.tests import common
from odoo.exceptions import ValidationError
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestResources(common.SlidesCase):

    @users('user_officer')
    @mute_logger('odoo')
    def test_constraints(self):
        link = self.env["slide.slide.resource"].create({
            'name': 'Test Link',
            'resource_type': 'url',
            'link': 'https://www.example.com',
            'slide_id': self.slide.id,
        })
        self.assertFalse(link.data)

        resource = self.env["slide.slide.resource"].create({
            'name': 'Test Resource',
            'resource_type': 'file',
            'data': '1111',
            'slide_id': self.slide.id,
        })
        self.assertFalse(resource.link)

        self.assertEqual(len(self.slide.slide_resource_ids), 2)
        with self.assertRaises(ValidationError, msg="Cannot have a type link with a file"):
            self.env["slide.slide.resource"].create({
                'name': 'Raise Error Test Resource',
                'resource_type': 'url',
                'link': '1111',
                'data': '1111',
                'slide_id': self.slide.id,
            })
        self.assertEqual(len(self.slide.slide_resource_ids), 2)
        with self.assertRaises(IntegrityError, msg="Cannot have a type file with a link"):
            self.env["slide.slide.resource"].create({
                'name': 'Raise Error Test File With Link',
                'resource_type': 'file',
                'link': '1111',
                'slide_id': self.slide.id,
            })
        with self.assertRaises(IntegrityError, msg="Cannot have an empty link"):
            self.env["slide.slide.resource"].create({
                'name': 'Raise Error Test Empty URL',
                'resource_type': 'url',
                'slide_id': self.slide.id,
            })
