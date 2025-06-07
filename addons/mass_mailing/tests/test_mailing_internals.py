# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re
from ast import literal_eval
from datetime import datetime
from unittest.mock import patch

from freezegun import freeze_time
from psycopg2 import IntegrityError
from unittest.mock import patch

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.exceptions import ValidationError
from odoo.sql_db import Cursor
from odoo.tests import Form, HttpCase, users, tagged
from odoo.tools import mute_logger

BASE_64_STRING = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='


@tagged("mass_mailing")
class TestMassMailValues(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailValues, cls).setUpClass()
        cls._create_mailing_list()

    @users('user_marketing')
    def test_mailing_body_cropped_vml_image(self):
        """ Testing mail mailing responsive bg-image cropping for Outlook.

        Outlook needs background images to be converted to VML but there is no
        way to emulate `background-size: cover` that works for Windows Mail as
        well. We therefore need to crop the image in the VML version to mimick
        the style of other email clients.
        """
        attachment = {}
        def patched_get_image(self, url, session):
            return base64.b64decode(BASE_64_STRING)
        original_images_to_urls = self.env['mailing.mailing']._create_attachments_from_inline_images
        def patched_images_to_urls(self, b64images):
            urls = original_images_to_urls(b64images)
            if len(urls) == 1:
                (attachment_id, attachment_token) = re.search(r'/web/image/(?P<id>[0-9]+)\?access_token=(?P<token>.*)', urls[0]).groups()
                attachment['id'] = attachment_id
                attachment['token'] = attachment_token
                return urls
            else:
                return []
        with patch("odoo.addons.mass_mailing.models.mailing.MassMailing._get_image_by_url",
                   new=patched_get_image), \
             patch("odoo.addons.mass_mailing.models.mailing.MassMailing._create_attachments_from_inline_images",
                   new=patched_images_to_urls):
            mailing = self.env['mailing.mailing'].create({
                'name': 'Test',
                'subject': 'Test',
                'state': 'draft',
                'mailing_model_id': self.env['ir.model']._get('res.partner').id,
                'body_html': """
                    <section>
                        <!--[if mso]>
                            <v:image src="https://www.example.com/image" style="width:100px;height:100px;"/>
                        <![endif]-->
                    </section>
                """,
            })
        self.assertEqual(str(mailing.body_html).strip(), f"""
                    <section>
                        <!--[if mso]>
                            <v:image src="/web/image/{attachment['id']}?access_token={attachment['token']}" style="width:100px;height:100px;"/>
                        <![endif]-->
                    </section>
        """.strip())

    @users('user_marketing')
    def test_mailing_body_inline_image(self):
        """ Testing mail mailing base64 image conversion to attachment.

        This test ensures that the base64 images are correctly converted to
        attachments, even when they appear in MSO conditional comments.
        """
        attachments = []
        original_images_to_urls = self.env['mailing.mailing']._create_attachments_from_inline_images
        def patched_images_to_urls(self, b64images):
            urls = original_images_to_urls(b64images)
            for url in urls:
                (attachment_id, attachment_token) = re.search(r'/web/image/(?P<id>[0-9]+)\?access_token=(?P<token>.*)', url).groups()
                attachments.append({
                    'id': attachment_id,
                    'token': attachment_token,
                })
            return urls
        with patch("odoo.addons.mass_mailing.models.mailing.MassMailing._create_attachments_from_inline_images",
                   new=patched_images_to_urls):
            mailing = self.env['mailing.mailing'].create({
                    'name': 'Test',
                    'subject': 'Test',
                    'state': 'draft',
                    'mailing_model_id': self.env['ir.model']._get('res.partner').id,
                    'body_html': f"""
                        <section>
                            <img src="data:image/png;base64,{BASE_64_STRING}0">
                            <img src="data:image/jpg;base64,{BASE_64_STRING}1">
                            <div style='color: red; background-image:url("data:image/jpg;base64,{BASE_64_STRING}2"); display: block;'/>
                            <div style="color: red; background-image:url('data:image/jpg;base64,{BASE_64_STRING}3'); display: block;"/>
                            <div style="color: red; background-image:url(&quot;data:image/jpg;base64,{BASE_64_STRING}4&quot;); display: block;"/>
                            <div style="color: red; background-image:url(&#34;data:image/jpg;base64,{BASE_64_STRING}5&#34;); display: block;"/>
                            <div style="color: red; background-image:url(data:image/jpg;base64,{BASE_64_STRING}6); display: block;"/>
                            <div style="color: red; background-image: url(data:image/jpg;base64,{BASE_64_STRING}7); background: url('data:image/jpg;base64,{BASE_64_STRING}8'); display: block;"/>
                            <!--[if mso]>
                                <img src="data:image/png;base64,{BASE_64_STRING}9">Fake url, in text: img src="data:image/png;base64,{BASE_64_STRING}"
                                Fake url, in text: img src="data:image/png;base64,{BASE_64_STRING}"
                                <img src="data:image/jpg;base64,{BASE_64_STRING}10">
                                <div style='color: red; background-image:url("data:image/jpg;base64,{BASE_64_STRING}11"); display: block;'>Fake url, in text: style="background-image:url('data:image/png;base64,{BASE_64_STRING}');"
                                Fake url, in text: style="background-image:url('data:image/png;base64,{BASE_64_STRING}');"</div>
                                <div style="color: red; background-image:url('data:image/jpg;base64,{BASE_64_STRING}12'); display: block;"/>
                                <div style="color: red; background-image:url(&quot;data:image/jpg;base64,{BASE_64_STRING}13&quot;); display: block;"/>
                                <div style="color: red; background-image:url(&#34;data:image/jpg;base64,{BASE_64_STRING}14&#34;); display: block;"/>
                                <div style="color: red; background-image:url(data:image/jpg;base64,{BASE_64_STRING}15); display: block;"/>
                                <div style="color: red; background-image: url(data:image/jpg;base64,{BASE_64_STRING}16); background: url('data:image/jpg;base64,{BASE_64_STRING}17'); display: block;"/>
                            <![endif]-->
                            <img src="data:image/png;base64,{BASE_64_STRING}0">
                        </section>
                    """,
                })
        self.assertEqual(len(attachments), 19)
        self.assertEqual(attachments[0]['id'], attachments[18]['id'])
        self.assertEqual(str(mailing.body_html).strip(), f"""
                        <section>
                            <img src="/web/image/{attachments[0]['id']}?access_token={attachments[0]['token']}"/>
                            <img src="/web/image/{attachments[1]['id']}?access_token={attachments[1]['token']}"/>
                            <div style="color: red; background-image:url(&quot;/web/image/{attachments[2]['id']}?access_token={attachments[2]['token']}&quot;); display: block;"/>
                            <div style="color: red; background-image:url('/web/image/{attachments[3]['id']}?access_token={attachments[3]['token']}'); display: block;"/>
                            <div style="color: red; background-image:url(&quot;/web/image/{attachments[4]['id']}?access_token={attachments[4]['token']}&quot;); display: block;"/>
                            <div style="color: red; background-image:url(&quot;/web/image/{attachments[5]['id']}?access_token={attachments[5]['token']}&quot;); display: block;"/>
                            <div style="color: red; background-image:url(/web/image/{attachments[6]['id']}?access_token={attachments[6]['token']}); display: block;"/>
                            <div style="color: red; background-image: url(/web/image/{attachments[7]['id']}?access_token={attachments[7]['token']}); background: url('/web/image/{attachments[8]['id']}?access_token={attachments[8]['token']}'); display: block;"/>
                            <!--[if mso]>
                                <img src="/web/image/{attachments[9]['id']}?access_token={attachments[9]['token']}">Fake url, in text: img src="data:image/png;base64,{BASE_64_STRING}"
                                Fake url, in text: img src="data:image/png;base64,{BASE_64_STRING}"
                                <img src="/web/image/{attachments[10]['id']}?access_token={attachments[10]['token']}">
                                <div style='color: red; background-image:url("/web/image/{attachments[11]['id']}?access_token={attachments[11]['token']}"); display: block;'>Fake url, in text: style="background-image:url('data:image/png;base64,{BASE_64_STRING}');"
                                Fake url, in text: style="background-image:url('data:image/png;base64,{BASE_64_STRING}');"</div>
                                <div style="color: red; background-image:url('/web/image/{attachments[12]['id']}?access_token={attachments[12]['token']}'); display: block;"/>
                                <div style="color: red; background-image:url(&quot;/web/image/{attachments[13]['id']}?access_token={attachments[13]['token']}&quot;); display: block;"/>
                                <div style="color: red; background-image:url(&#34;/web/image/{attachments[14]['id']}?access_token={attachments[14]['token']}&#34;); display: block;"/>
                                <div style="color: red; background-image:url(/web/image/{attachments[15]['id']}?access_token={attachments[15]['token']}); display: block;"/>
                                <div style="color: red; background-image: url(/web/image/{attachments[16]['id']}?access_token={attachments[16]['token']}); background: url('/web/image/{attachments[17]['id']}?access_token={attachments[17]['token']}'); display: block;"/>
                            <![endif]-->
                            <img src="/web/image/{attachments[18]['id']}?access_token={attachments[18]['token']}"/>
                        </section>
        """.strip())

    @users('user_marketing')
    def test_mailing_body_responsive(self):
        """ Testing mail mailing responsive mail body

        Reference: https://litmus.com/community/learning/24-how-to-code-a-responsive-email-from-scratch
        https://www.campaignmonitor.com/css/link-element/link-in-head/

        This template is meant to put inline CSS into an email's head
        """
        recipient = self.env['res.partner'].create({
            'name': 'Mass Mail Partner',
            'email': 'Customer <test.customer@example.com>',
        })
        mailing = self.env['mailing.mailing'].create({
            'name': 'Test',
            'subject': 'Test',
            'state': 'draft',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })

        composer = self.env['mail.compose.message'].with_user(self.user_marketing).with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': 'res.partner',
            'default_res_ids': recipient.ids,
        }).create({
            'subject': 'Mass Mail Responsive',
            'body': 'I am Responsive body',
            'mass_mailing_id': mailing.id
        })

        mail_values = composer._prepare_mail_values([recipient.id])
        body_html = mail_values[recipient.id]['body_html']

        self.assertIn('<!DOCTYPE html>', body_html)
        self.assertIn('<head>', body_html)
        self.assertIn('viewport', body_html)
        # This is important: we need inline css, and not <link/>
        self.assertIn('@media', body_html)
        self.assertIn('I am Responsive body', body_html)

    @users('user_marketing')
    def test_mailing_computed_fields(self):
        # Create on res.partner, with default values for computed fields
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'mail',
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
        self.assertEqual(mailing.user_id, self.user_marketing)
        self.assertEqual(mailing.medium_id, self.env.ref('utm.utm_medium_email'))
        self.assertEqual(mailing.mailing_model_name, 'res.partner')
        self.assertEqual(mailing.mailing_model_real, 'res.partner')
        self.assertEqual(mailing.reply_to_mode, 'new')
        self.assertEqual(mailing.reply_to, self.user_marketing.email_formatted)
        # default for partner: remove blacklisted
        self.assertEqual(literal_eval(mailing.mailing_domain), [('is_blacklisted', '=', False)])
        # update domain
        mailing.write({
            'mailing_domain': [('email', 'ilike', 'test.example.com')]
        })
        self.assertEqual(literal_eval(mailing.mailing_domain), [('email', 'ilike', 'test.example.com')])

        # reset mailing model -> reset domain; set reply_to -> keep it
        mailing.write({
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'reply_to': self.email_reply_to,
        })
        self.assertEqual(mailing.mailing_model_name, 'mailing.list')
        self.assertEqual(mailing.mailing_model_real, 'mailing.contact')
        self.assertEqual(mailing.reply_to_mode, 'new')
        self.assertEqual(mailing.reply_to, self.email_reply_to)
        # default for mailing list: depends upon contact_list_ids
        self.assertEqual(literal_eval(mailing.mailing_domain), [('list_ids', 'in', [])])
        mailing.write({
            'contact_list_ids': [(4, self.mailing_list_1.id), (4, self.mailing_list_2.id)]
        })
        self.assertEqual(literal_eval(mailing.mailing_domain), [('list_ids', 'in', (self.mailing_list_1 | self.mailing_list_2).ids)])

        # reset mailing model -> reset domain and reply to mode
        mailing.write({
            'mailing_model_id': self.env['ir.model']._get('discuss.channel').id,
        })
        self.assertEqual(mailing.mailing_model_name, 'discuss.channel')
        self.assertEqual(mailing.mailing_model_real, 'discuss.channel')
        self.assertEqual(mailing.reply_to_mode, 'update')
        self.assertFalse(mailing.reply_to)

    @users('user_marketing')
    def test_mailing_computed_fields_domain_w_filter(self):
        """ Test domain update, involving mailing.filters added in 15.1. """
        # Create on res.partner, with default values for computed fields
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'mail',
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
        # default for partner: remove blacklisted
        self.assertEqual(literal_eval(mailing.mailing_domain), [('is_blacklisted', '=', False)])

        # prepare initial data
        filter_1, filter_2, filter_3 = self.env['mailing.filter'].create([
            {'name': 'General channel',
             'mailing_domain' : [('name', '=', 'general')],
             'mailing_model_id': self.env['ir.model']._get('discuss.channel').id,
            },
            {'name': 'LLN City',
             'mailing_domain' : [('city', 'ilike', 'LLN')],
             'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            },
            {'name': 'Email based',
             'mailing_domain' : [('email', 'ilike', 'info@odoo.com')],
             'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            }
        ])

        # check that adding mailing_filter_id updates domain correctly
        mailing.mailing_filter_id = filter_2
        self.assertEqual(literal_eval(mailing.mailing_domain), literal_eval(filter_2.mailing_domain))

        # cannot set a filter linked to another model
        with self.assertRaises(ValidationError):
            mailing.mailing_filter_id = filter_1

        # resetting model should reset domain, even if filter was chosen previously
        mailing.mailing_model_id = self.env['ir.model']._get('discuss.channel').id
        self.assertEqual(literal_eval(mailing.mailing_domain), [])

        # changing the filter should update the mailing domain correctly
        mailing.mailing_filter_id = filter_1
        self.assertEqual(literal_eval(mailing.mailing_domain), literal_eval(filter_1.mailing_domain))

        # changing the domain should not empty the mailing_filter_id
        mailing.mailing_domain = "[('email', 'ilike', 'info_be@odoo.com')]"
        self.assertEqual(mailing.mailing_filter_id, filter_1, "Filter should not be unset even if domain is changed")

        # deleting the filter record should not delete the domain on mailing
        mailing.mailing_model_id = self.env['ir.model']._get('res.partner').id
        mailing.mailing_filter_id = filter_3
        filter_3_domain = filter_3.mailing_domain
        self.assertEqual(literal_eval(mailing.mailing_domain), literal_eval(filter_3_domain))
        filter_3.unlink()  # delete the filter record
        self.assertFalse(mailing.mailing_filter_id, "Should unset filter if it is deleted")
        self.assertEqual(literal_eval(mailing.mailing_domain), literal_eval(filter_3_domain), "Should still have the same domain")

    @users('user_marketing')
    def test_mailing_computed_fields_default(self):
        mailing = self.env['mailing.mailing'].with_context(
            default_mailing_domain=repr([('email', 'ilike', 'test.example.com')])
        ).create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'mail',
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
        self.assertEqual(literal_eval(mailing.mailing_domain), [('email', 'ilike', 'test.example.com')])

    @users('user_marketing')
    def test_mailing_computed_fields_default_email_from(self):
        # Testing if the email_from is correctly computed when an
        # alias domain for the company is set

        # Setup mail outgoing server for use cases

        from_filter_match, from_filter_missmatch = self.env['ir.mail_server'].sudo().create([
            # Case where alias domain is set and there is a default outgoing email server
            # for mass mailing. from_filter matches domain of company alias domain
            # before record creation
            {
                    'name' : 'mass_mailing_test_match_from_filter',
                    'from_filter' : self.alias_domain,
                    'smtp_host' : 'not_real@smtp.com',
            },
            # Case where alias domain is set and there is a default outgoing email server
            # for mass mailing. from_filter DOES NOT match domain of company alias domain
            # before record creation
            {
                    'name' : 'mass_mailing_test_from_missmatch',
                    'from_filter' : 'test.com',
                    'smtp_host' : 'not_real@smtp.com',
            },
        ])

        # Expected combos of server vs FROM values

        servers = [
            self.env['ir.mail_server'],
            from_filter_match,
            from_filter_missmatch,
        ]
        expected_from_all = [
            self.env.user.email_formatted,  # default when no server
            self.env.user.company_id.alias_domain_id.default_from_email,  # matches company alias domain
            self.env.user.email_formatted,  # not matching from filter -> back to user from
        ]

        for mail_server, expected_from in zip(servers, expected_from_all):
            with self.subTest(server_name=mail_server.name):
                # When a mail server is set, we update the mass mailing
                # settings to designate a dedicated outgoing email server
                if mail_server:
                    self.env['res.config.settings'].sudo().create({
                        'mass_mailing_mail_server_id' : mail_server.id,
                        'mass_mailing_outgoing_mail_server' : mail_server,
                    }).execute()

                # Create mailing
                mailing = self.env['mailing.mailing'].create({
                    'name': f'TestMailing {mail_server.name}',
                    'subject': f'Test {mail_server.name}',
                })

                # Check email_from
                self.assertEqual(mailing.email_from, expected_from)

                # If configured, check if dedicated email outgoing server is
                # on mailing record
                self.assertEqual(mailing.mail_server_id, mail_server)

    @users('user_marketing')
    def test_mailing_computed_fields_form(self):
        mailing_form = Form(self.env['mailing.mailing'].with_context(
            default_mailing_domain="[('email', 'ilike', 'test.example.com')]",
            default_mailing_model_id=self.env['ir.model']._get('res.partner').id,
        ))
        self.assertEqual(
            literal_eval(mailing_form.mailing_domain),
            [('email', 'ilike', 'test.example.com')],
        )
        self.assertEqual(mailing_form.mailing_model_real, 'res.partner')

    @mute_logger('odoo.sql_db')
    @users('user_marketing')
    def test_mailing_trace_values(self):
        recipient = self.partner_employee

        # both void and 0 are invalid, document should have an id != 0
        with self.assertRaises(IntegrityError):
            self.env['mailing.trace'].create({
                'model': recipient._name,
            })
        with self.assertRaises(IntegrityError):
            self.env['mailing.trace'].create({
                'model': recipient._name,
                'res_id': 0,
            })
        with self.assertRaises(IntegrityError):
            self.env['mailing.trace'].create({
                'res_id': 3,
            })

        activity = self.env['mailing.trace'].create({
            'model': recipient._name,
            'res_id': recipient.id,
        })
        with self.assertRaises(IntegrityError):
            activity.write({'model': False})
            self.env.flush_all()
        with self.assertRaises(IntegrityError):
            activity.write({'res_id': False})
            self.env.flush_all()
        with self.assertRaises(IntegrityError):
            activity.write({'res_id': 0})
            self.env.flush_all()

    def test_mailing_editor_created_attachments(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'mail',
            'body_html': '<p>Hello</p>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
        blob_b64 = base64.b64encode(b'blob1')

        # Created when uploading an image
        original_svg_attachment = self.env['ir.attachment'].create({
            "name": "test SVG",
            "mimetype": "image/svg+xml",
            "datas": blob_b64,
            "public": True,
            "res_model": "mailing.mailing",
            "res_id": mailing.id,
        })

        # Created when saving the mass_mailing
        png_duplicate_of_svg_attachment = self.env['ir.attachment'].create({
            "name": "test SVG duplicate",
            "mimetype": "image/png",
            "datas": blob_b64,
            "public": True,
            "res_model": "mailing.mailing",
            "res_id": mailing.id,
            "original_id": original_svg_attachment.id
        })

        # Created by uploading new image
        original_png_attachment = self.env['ir.attachment'].create({
            "name": "test PNG",
            "mimetype": "image/png",
            "datas": blob_b64,
            "public": True,
            "res_model": "mailing.mailing",
            "res_id": mailing.id,
        })

        # Created by modify_image in editor controller
        self.env['ir.attachment'].create({
            "name": "test PNG duplicate",
            "mimetype": "image/png",
            "datas": blob_b64,
            "public": True,
            "res_model": "mailing.mailing",
            "res_id": mailing.id,
            "original_id": original_png_attachment.id
        })

        mail_thread_attachments = mailing._get_mail_thread_data_attachments()
        self.assertSetEqual(set(mail_thread_attachments.ids), {png_duplicate_of_svg_attachment.id, original_png_attachment.id})

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_process_mailing_queue_without_html_body(self):
        """ Test mailing with past schedule date and without any html body """
        mailing = self.env['mailing.mailing'].create({
                'name': 'mailing',
                'subject': 'some subject',
                'mailing_model_id': self.env['ir.model']._get('res.partner').id,
                'preview': "Check it out before its too late",
                'body_html': False,
                'schedule_date': datetime(2023, 2, 17, 11, 0),
            })
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertFalse(mailing.body_html)
        self.assertEqual(mailing.mailing_model_name, 'res.partner')


@tagged("mass_mailing", "utm")
class TestMassMailUTM(MassMailCommon):

    @freeze_time('2022-01-02')
    @patch.object(Cursor, 'now', lambda *args, **kwargs: datetime(2022, 1, 2))
    @users('user_marketing')
    def test_mailing_unique_name(self):
        """Test that the names are generated and unique for each mailing.

        If the name is missing, it's generated from the subject. Then we should ensure
        that this generated name is unique.
        """
        mailing_0 = self.env['mailing.mailing'].create({'subject': 'First subject'})
        self.assertEqual(mailing_0.name, 'First subject (Mass Mailing created on 2022-01-02)')

        mailing_1, mailing_2, mailing_3, mailing_4, mailing_5, mailing_6 = self.env['mailing.mailing'].create([{
            'subject': 'First subject',
        }, {
            'subject': 'First subject',
        }, {
            'subject': 'First subject',
            'source_id': self.env['utm.source'].create({'name': 'Custom Source'}).id,
        }, {
            'subject': 'First subject',
            'name': 'Mailing',
        }, {
            'subject': 'Second subject',
            'name': 'Mailing',
        }, {
            'subject': 'Second subject',
        }])

        self.assertEqual(mailing_0.name, 'First subject (Mass Mailing created on 2022-01-02)')
        self.assertEqual(mailing_1.name, 'First subject (Mass Mailing created on 2022-01-02) [2]')
        self.assertEqual(mailing_2.name, 'First subject (Mass Mailing created on 2022-01-02) [3]')
        self.assertEqual(mailing_3.name, 'Custom Source')
        self.assertEqual(mailing_4.name, 'Mailing')
        self.assertEqual(mailing_5.name, 'Mailing [2]')
        self.assertEqual(mailing_6.name, 'Second subject (Mass Mailing created on 2022-01-02)')

        # should generate same name (coming from same subject)
        mailing_0.subject = 'First subject'
        self.assertEqual(mailing_0.name, 'First subject (Mass Mailing created on 2022-01-02)',
            msg='The name should not be updated')

        # take a (long) existing name -> should increment
        mailing_0.name = 'Second subject (Mass Mailing created on 2022-01-02)'
        self.assertEqual(mailing_0.name, 'Second subject (Mass Mailing created on 2022-01-02) [2]',
            msg='The name must be unique, it was already taken')

        # back to first subject: not linked to any record so should take it back
        mailing_0.subject = 'First subject'
        self.assertEqual(mailing_0.name, 'First subject (Mass Mailing created on 2022-01-02)',
            msg='The name should be back to first one')

    def test_mailing_create_with_context(self):
        """ Test that the default_name provided via context is ignored to prevent constraint violations."""
        mailing_1, mailing_2 = self.env["mailing.mailing"].create([
            {
                "subject": "First subject",
                "name": "Mailing",
            },
            {
                "subject": "Second subject",
                "name": "Mailing",
            },
        ])
        self.assertEqual(mailing_1.name, "Mailing")
        self.assertEqual(mailing_2.name, "Mailing [2]")
        mailing_3 = self.env["mailing.mailing"].with_context({"default_name": "Mailing"}).create({"subject": "Third subject"})
        self.assertEqual(mailing_3.name, "Mailing [3]")


@tagged('mass_mailing')
class TestMassMailFeatures(MassMailCommon, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailFeatures, cls).setUpClass()
        cls._create_mailing_list()

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_cron_trigger(self):
        """ Technical test to ensure the cron is triggered at the correct
        time """

        cron_id = self.env.ref('mass_mailing.ir_cron_mass_mailing_queue').id
        partner = self.env['res.partner'].create({
            'name': 'Jean-Alphonce',
            'email': 'jeanalph@example.com',
        })
        common_mailing_values = {
            'name': 'Knock knock',
            'subject': "Who's there?",
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'mailing_domain': [('id', '=', partner.id)],
            'body_html': 'The marketing mailing test.',
            'schedule_type': 'scheduled',
        }

        now = datetime(2021, 2, 5, 16, 43, 20)
        then = datetime(2021, 2, 7, 12, 0, 0)

        with freeze_time(now):
            for (test, truth) in [(False, now), (then, then)]:
                with self.subTest(schedule_date=test):
                    with self.capture_triggers(cron_id) as capt:
                        mailing = self.env['mailing.mailing'].create({
                            **common_mailing_values,
                            'schedule_date': test,
                        })
                        mailing.action_put_in_queue()
                    capt.records.ensure_one()
                    self.assertLessEqual(capt.records.call_at, truth)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_deletion(self):
        """ Test deletion in various use case, depending on reply-to """
        # 1- Keep archives and reply-to set to 'answer = new thread'
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestSource',
            'subject': 'TestDeletion',
            'body_html': "<div>Hello {object.name}</div>",
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'contact_list_ids': [(6, 0, self.mailing_list_1.ids)],
            'keep_archives': True,
            'reply_to_mode': 'new',
            'reply_to': self.email_reply_to,
        })
        self.assertEqual(self.mailing_list_1.contact_ids.message_ids, self.env['mail.message'])

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing.action_send_mail()

        self.assertEqual(len(self._mails), 3)
        self.assertEqual(len(self._new_mails.exists()), 3)
        self.assertEqual(len(self.mailing_list_1.contact_ids.message_ids), 3)

        # 2- Keep archives and reply-to set to 'answer = update thread'
        self.mailing_list_1.contact_ids.message_ids.unlink()
        mailing = mailing.copy()
        mailing.write({
            'reply_to_mode': 'update',
        })
        self.assertEqual(self.mailing_list_1.contact_ids.message_ids, self.env['mail.message'])

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing.action_send_mail()

        self.assertEqual(len(self._mails), 3)
        self.assertEqual(len(self._new_mails.exists()), 3)
        self.assertEqual(len(self.mailing_list_1.contact_ids.message_ids), 3)

        # 3- Remove archives and reply-to set to 'answer = new thread'
        self.mailing_list_1.contact_ids.message_ids.unlink()
        mailing = mailing.copy()
        mailing.write({
            'keep_archives': False,
            'reply_to_mode': 'new',
            'reply_to': self.email_reply_to,
        })
        self.assertEqual(self.mailing_list_1.contact_ids.message_ids, self.env['mail.message'])

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing.action_send_mail()

        self.assertEqual(len(self._mails), 3)
        self.assertEqual(len(self._new_mails.exists()), 0)
        self.assertEqual(self.mailing_list_1.contact_ids.message_ids, self.env['mail.message'])

        # 4- Remove archives and reply-to set to 'answer = update thread'
        # Imply keeping mail.message for gateway reply)
        self.mailing_list_1.contact_ids.message_ids.unlink()
        mailing = mailing.copy()
        mailing.write({
            'keep_archives': False,
            'reply_to_mode': 'update',
        })
        self.assertEqual(self.mailing_list_1.contact_ids.message_ids, self.env['mail.message'])

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing.action_send_mail()

        self.assertEqual(len(self._mails), 3)
        self.assertEqual(len(self._new_mails.exists()), 0)
        self.assertEqual(len(self.mailing_list_1.contact_ids.message_ids), 3)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_on_res_partner(self):
        """ Test mailing on res.partner model: ensure default recipients are
        correctly computed """
        partner_a = self.env['res.partner'].create({
            'name': 'test email 1',
            'email': 'test1@example.com',
        })
        partner_b = self.env['res.partner'].create({
            'name': 'test email 2',
            'email': 'test2@example.com',
        })
        self.env['mail.blacklist'].create({'email': 'Test2@example.com',})

        mailing = self.env['mailing.mailing'].create({
            'name': 'One',
            'subject': 'One',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'mailing_domain': [('id', 'in', (partner_a | partner_b).ids)],
            'body_html': 'This is mass mail marketing demo'
        })
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'partner': partner_a},
             {'partner': partner_b, 'trace_status': 'cancel', 'failure_type': 'mail_bl'}],
            mailing, partner_a + partner_b, check_mail=True
        )

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_shortener(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestSource',
            'subject': 'TestShortener',
            'body_html': """<div>
Hi,
<t t-set="url" t-value="'www.odoo.com'"/>
<t t-set="httpurl" t-value="'https://www.odoo.eu'"/>
Website0: <a id="url0" t-attf-href="https://www.odoo.tz/my/{{object.name}}">https://www.odoo.tz/my/<t t-esc="object.name"/></a>
Website1: <a id="url1" href="https://www.odoo.be">https://www.odoo.be</a>
Website2: <a id="url2" t-attf-href="https://{{url}}">https://<t t-esc="url"/></a>
Website3: <a id="url3" t-att-href="httpurl"><t t-esc="httpurl"/></a>
External1: <a id="url4" href="https://www.example.com/foo/bar?baz=qux">Youpie</a>
Email: <a id="url5" href="mailto:test@odoo.com">test@odoo.com</a></div>""",
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'reply_to_mode': 'new',
            'reply_to': self.email_reply_to,
            'contact_list_ids': [(6, 0, self.mailing_list_1.ids)],
            'keep_archives': True,
        })

        mailing.action_put_in_queue()

        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'email': 'fleurus@example.com'},
             {'email': 'gorramts@example.com'},
             {'email': 'ybrant@example.com'}],
            mailing, self.mailing_list_1.contact_ids, check_mail=True
        )

        for contact in self.mailing_list_1.contact_ids:
            new_mail = self._find_mail_mail_wrecord(contact)
            for link_info in [('url0', 'https://www.odoo.tz/my/%s' % contact.name, True),
                              ('url1', 'https://www.odoo.be', True),
                              ('url2', 'https://www.odoo.com', True),
                              ('url3', 'https://www.odoo.eu', True),
                              ('url4', 'https://www.example.com/foo/bar?baz=qux', True),
                              ('url5', 'mailto:test@odoo.com', False)]:
                # TDE FIXME: why going to mail message id ? mail.body_html seems to fail, check
                link_params = {'utm_medium': 'Email', 'utm_source': mailing.name}
                if link_info[0] == 'url4':
                    link_params['baz'] = 'qux'
                self.assertLinkShortenedHtml(
                    new_mail.mail_message_id.body,
                    link_info,
                    link_params=link_params,
                )


@tagged("mail_mail")
class TestMailingHeaders(MassMailCommon, HttpCase):
    """ Test headers + linked controllers """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_mailing_list()
        cls.test_mailing = cls.env['mailing.mailing'].with_user(cls.user_marketing).create({
            "body_html": """
<p>Hello <t t-out="object.name"/>
    <a href="/unsubscribe_from_list">UNSUBSCRIBE</a>
    <a href="/view">VIEW</a>
</p>""",
            "contact_list_ids": [(4, cls.mailing_list_1.id)],
            "mailing_model_id": cls.env["ir.model"]._get("mailing.list").id,
            "mailing_type": "mail",
            "name": "TestMailing",
            "subject": "Test for {{ object.name }}",
        })

    @users('user_marketing')
    def test_mailing_unsubscribe_headers(self):
        """ Check unsubscribe headers are present in outgoing emails and work
        as one-click """
        test_mailing = self.test_mailing.with_env(self.env)
        test_mailing.action_put_in_queue()

        with self.mock_mail_gateway(mail_unlink_sent=False):
            test_mailing.action_send_mail()

        for contact in self.mailing_list_1.contact_ids:
            new_mail = self._find_mail_mail_wrecord(contact)
            # check mail.mail still have default links
            self.assertIn("/unsubscribe_from_list", new_mail.body)
            self.assertIn("/view", new_mail.body)

            # check outgoing email headers (those are put into outgoing email
            # not in the mail.mail record)
            email = self._find_sent_mail_wemail(contact.email)
            headers = email.get("headers")
            unsubscribe_oneclick_url = test_mailing._get_unsubscribe_oneclick_url(contact.email, contact.id)
            self.assertTrue(headers, "Mass mailing emails should have headers for unsubscribe")
            self.assertEqual(headers.get("List-Unsubscribe"), f"<{unsubscribe_oneclick_url}>")
            self.assertEqual(headers.get("List-Unsubscribe-Post"), "List-Unsubscribe=One-Click")
            self.assertEqual(headers.get("Precedence"), "list")

            # check outgoing email has real links
            self.assertNotIn("/unsubscribe_from_list", email["body"])

            # unsubscribe in one-click
            unsubscribe_oneclick_url = headers["List-Unsubscribe"].strip("<>")
            self.opener.post(unsubscribe_oneclick_url)

            # should be unsubscribed
            self.assertTrue(contact.subscription_ids.opt_out)


class TestMailingScheduleDateWizard(MassMailCommon):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('user_marketing')
    def test_mailing_schedule_date(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'mailing',
            'subject': 'some subject'
        })
        # create a schedule date wizard
        wizard_form = Form(
            self.env['mailing.mailing.schedule.date'].with_context(default_mass_mailing_id=mailing.id))

        # set a schedule date
        wizard_form.schedule_date = datetime(2021, 4, 30, 9, 0)
        wizard = wizard_form.save()
        wizard.action_schedule_date()

        # assert that the schedule_date and schedule_type fields are correct and that the mailing is put in queue
        self.assertEqual(mailing.schedule_date, datetime(2021, 4, 30, 9, 0))
        self.assertEqual(mailing.schedule_type, 'scheduled')
        self.assertEqual(mailing.state, 'in_queue')


class TestMassMailingActions(MassMailCommon):
    def test_mailing_action_open(self):
        mass_mailings = self.env['mailing.mailing'].create([
            {'subject': 'First subject'},
            {'subject': 'Second subject'}
        ])
        # Create two traces: one linked to the created mass.mailing and one not (action should open only the first)
        self.env["mailing.trace"].create([{
                "trace_status": "open",
                "mass_mailing_id": mass_mailings[0].id,
                "model": "res.partner",
                "res_id": self.partner_admin.id,
            }, {
                "trace_status": "open",
                "mass_mailing_id": mass_mailings[1].id,
                "model": "res.partner",
                "res_id": self.partner_employee.id,
            }
        ])
        results = mass_mailings[0].action_view_opened()
        results_partner = self.env["res.partner"].search(results['domain'])
        self.assertEqual(results_partner, self.partner_admin, "Trace leaked from mass_mailing_2 to mass_mailing_1")
