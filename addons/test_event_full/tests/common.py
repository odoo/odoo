# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, time

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.addons.event_crm.tests.common import EventCrmCase
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sales_team.tests.common import TestSalesCommon
from odoo.addons.website.tests.test_website_visitor import MockVisitor


class TestEventFullCommon(EventCrmCase, TestSalesCommon, MockVisitor):

    @classmethod
    def setUpClass(cls):
        super(TestEventFullCommon, cls).setUpClass()
        cls._init_mail_gateway()

        # Context data: dates
        # ------------------------------------------------------------

        # Mock dates to have reproducible computed fields based on time
        cls.reference_now = datetime(2021, 12, 1, 10, 0, 0)
        cls.reference_today = datetime(2021, 12, 1)

        # Users and contacts
        # ------------------------------------------------------------

        cls.admin_user = cls.env.ref('base.user_admin')
        cls.admin_user.write({
            'country_id': cls.env.ref('base.be').id,
            'login': 'admin',
            'notification_type': 'inbox',
        })
        cls.company_admin = cls.admin_user.company_id
        # set country in order to format Belgian numbers
        cls.company_admin.write({
            'country_id': cls.env.ref('base.be').id,
        })
        cls.event_user = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            company_ids=[(4, cls.company_admin.id)],
            country_id=cls.env.ref('base.be').id,
            groups='base.group_user,base.group_partner_manager,event.group_event_user',
            email='e.e@example.com',
            login='event_user',
            name='Ernest Employee',
            notification_type='inbox',
            signature='--\nErnest',
        )

        cls.customer = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.be').id,
            'email': 'customer.test@example.com',
            'name': 'Test Customer',
            'mobile': '0456123456',
            'phone': '0456123456',
        })
        # make a SO for a customer, selling some tickets
        cls.customer_so = cls.env['sale.order'].with_user(cls.user_sales_salesman).create({
            'partner_id': cls.event_customer.id,
        })

        # Side records for event main records
        # ------------------------------------------------------------

        cls.ticket_product = cls.env['product.product'].create({
            'description_sale': 'Ticket Product Description',
            'detailed_type': 'event',
            'list_price': 10,
            'name': 'Test Registration Product',
            'standard_price': 30.0,
        })
        cls.booth_product = cls.env['product.product'].create({
            'description_sale': 'Booth Product Description',
            'detailed_type': 'event_booth',
            'list_price': 20,
            'name': 'Test Booth Product',
            'standard_price': 60.0,
        })

        cls.tag_categories = cls.env['event.tag.category'].create([
            {'is_published': True, 'name': 'Published Category'},
            {'is_published': False, 'name': 'Unpublished Category'},
        ])
        cls.tags = cls.env['event.tag'].create([
            {'category_id': cls.tag_categories[0].id, 'name': 'PubTag1'},
            {'category_id': cls.tag_categories[0].id, 'color': 0, 'name': 'PubTag2'},
            {'category_id': cls.tag_categories[1].id, 'name': 'UnpubTag1'},
        ])

        cls.event_booth_categories = cls.env['event.booth.category'].create([
            {'description': '<p>Standard</p>',
             'name': 'Standard',
             'product_id': cls.booth_product.id,
            },
            {'description': '<p>Premium</p>',
             'name': 'Premium',
             'product_id': cls.booth_product.id,
             'price': 90,
            }
        ])

        cls.sponsor_types = cls.env['event.sponsor.type'].create([
            {'name': 'GigaTop',
             'sequence': 1,
            }
        ])
        cls.sponsor_partners = cls.env['res.partner'].create([
            {'country_id': cls.env.ref('base.be').id,
             'email': 'event.sponsor@example.com',
             'name': 'EventSponsor',
             'phone': '04856112233',
            }
        ])

        # Event type
        # ------------------------------------------------------------
        test_registration_report = cls.env.ref('test_event_full.event_registration_report_test')
        subscription_template = cls.env.ref('event.event_subscription')
        subscription_template.write({'report_template': test_registration_report.id})
        cls.test_event_type = cls.env['event.type'].create({
            'auto_confirm': True,
            'default_timezone': 'Europe/Paris',
            'event_type_booth_ids': [
                (0, 0, {'booth_category_id': cls.event_booth_categories[0].id,
                        'name': 'Standard Booth',
                       }
                ),
                (0, 0, {'booth_category_id': cls.event_booth_categories[0].id,
                        'name': 'Standard Booth 2',
                       }
                ),
                (0, 0, {'booth_category_id': cls.event_booth_categories[1].id,
                        'name': 'Premium Booth',
                       }
                ),
                (0, 0, {'booth_category_id': cls.event_booth_categories[1].id,
                        'name': 'Premium Booth 2',
                       }
                ),
            ],
            'event_type_mail_ids': [
                (0, 0, {'interval_unit': 'now',  # right at subscription
                        'interval_type': 'after_sub',
                        'notification_type': 'mail',
                        'template_ref': 'mail.template,%i' % subscription_template.id,
                       }
                ),
                (0, 0, {'interval_nbr': 1,  # 1 days before event
                        'interval_unit': 'days',
                        'interval_type': 'before_event',
                        'notification_type': 'mail',
                        'template_ref': 'mail.template,%i' % cls.env['ir.model.data']._xmlid_to_res_id('event.event_reminder'),
                       }
                ),
                (0, 0, {'interval_nbr': 1,  # 1 days after event
                        'interval_unit': 'days',
                        'interval_type': 'after_event',
                        'notification_type': 'sms',
                        'template_ref': 'sms.template,%i' % cls.env['ir.model.data']._xmlid_to_res_id('event_sms.sms_template_data_event_reminder'),
                       }
                ),
            ],
            'event_type_ticket_ids': [
                (0, 0, {'description': 'Ticket1 Description',
                        'name': 'Ticket1',
                        'product_id': cls.ticket_product.id,
                        'seats_max': 10,
                       }
                ),
                (0, 0, {'description': 'Ticket2 Description',
                        'name': 'Ticket2',
                        'product_id': cls.ticket_product.id,
                        'price': 45,
                       }
                )
            ],
            'has_seats_limitation': True,
            'name': 'Test Type',
            'note': '<p>Template note</p>',
            'question_ids': [
                (0, 0, {'answer_ids':
                        [(0, 0, {'name': 'Q1-Answer1'}),
                         (0, 0, {'name': 'Q1-Answer2'}),
                        ],
                        'question_type': 'simple_choice',
                        'once_per_order': False,
                        'title': 'Question1',
                       }
                ),
                (0, 0, {'answer_ids':
                        [(0, 0, {'name': 'Q2-Answer1'}),
                         (0, 0, {'name': 'Q2-Answer2'}),
                        ],
                        'question_type': 'simple_choice',
                        'once_per_order': False,
                        'title': 'Question2',
                       }
                ),
                (0, 0, {'question_type': 'text_box',
                        'once_per_order': True,
                        'title': 'Question3',
                       }
                ),
            ],
            'seats_max': 30,
            'tag_ids': [(4, tag.id) for tag in cls.tags],
            'ticket_instructions': '<p>Ticket Instructions</p>',
            'website_menu': True,
        })

        # Stages
        cls.stage_def = cls.env['event.stage'].create({
            'name': 'First Stage',
            'sequence': 0,
        })

        # Event data
        # ------------------------------------------------------------

        cls.event_base_vals = {
            'name': 'Test Event',
            'date_begin': cls.reference_now + timedelta(days=1),
            'date_end': cls.reference_now + timedelta(days=5),
            'is_published': True,
        }

        cls.test_event = cls.env['event.event'].create({
            'name': 'Test Event',
            'auto_confirm': True,
            'date_begin': datetime.now() + timedelta(days=1),
            'date_end': datetime.now() + timedelta(days=5),
            'date_tz': 'Europe/Brussels',
            'event_type_id': cls.test_event_type.id,
            'is_published': True,
        })
        # update post-synchronize data
        ticket_1 = cls.test_event.event_ticket_ids.filtered(lambda t: t.name == 'Ticket1')
        ticket_2 = cls.test_event.event_ticket_ids.filtered(lambda t: t.name == 'Ticket2')
        ticket_1.start_sale_datetime = cls.reference_now + timedelta(hours=1)
        ticket_2.start_sale_datetime = cls.reference_now + timedelta(hours=2)

        # Website data
        # ------------------------------------------------------------

        cls.website = cls.env['website'].search([
            ('company_id', '=', cls.company_admin.id)
        ], limit=1)

        cls.customer_data = [
            {'email': 'customer.email.%02d@test.example.com' % x,
             'name': 'My Customer %02d' % x,
             'mobile': '04569999%02d' % x,
             'partner_id': False,
             'phone': '04560000%02d' % x,
            } for x in range(0, 10)
        ]
        cls.website_customer_data = [
            {'email': 'website.email.%02d@test.example.com' % x,
             'name': 'My Customer %02d' % x,
             'mobile': '04569999%02d' % x,
             'partner_id': cls.env.ref('base.public_partner').id,
             'phone': '04560000%02d' % x,
             'registration_answer_ids': [
                (0, 0, {
                    'question_id': cls.test_event.question_ids[0].id,
                    'value_answer_id': cls.test_event.question_ids[0].answer_ids[(x % 2)].id,
                }), (0, 0, {
                    'question_id': cls.test_event.question_ids[1].id,
                    'value_answer_id': cls.test_event.question_ids[1].answer_ids[(x % 2)].id,
                }), (0, 0, {
                    'question_id': cls.test_event.question_ids[2].id,
                    'value_text_box': 'CustomerAnswer%s' % x,
                })
             ],
            } for x in range(0, 10)
        ]
        cls.partners = cls.env['res.partner'].create([
            {'email': 'partner.email.%02d@test.example.com' % x,
             'name': 'PartnerCustomer',
             'mobile': '04569999%02d' % x,
             'phone': '04560000%02d' % x,
            } for x in range(0, 10)
        ])

    def assertLeadConvertion(self, rule, registrations, partner=None, **expected):
        super(TestEventFullCommon, self).assertLeadConvertion(rule, registrations, partner=partner, **expected)
        lead = self.env['crm.lead'].sudo().search([
            ('registration_ids', 'in', registrations.ids),
            ('event_lead_rule_id', '=', rule.id)
        ])

        for registration in registrations:
            if not registration.registration_answer_ids:
                continue
            for answer in registration.registration_answer_ids:
                self.assertIn(answer.question_id.title, lead.description)
                if answer.question_type == 'simple_choice':
                    self.assertIn(answer.value_answer_id.name, lead.description)
                else:
                    self.assertIn(answer.value_text_box, lead.description)  # better: check multi line


class TestWEventCommon(HttpCaseWithUserDemo, HttpCaseWithUserPortal, MockVisitor):

    def setUp(self):
        super(TestWEventCommon, self).setUp()

        # Context data: dates
        # ------------------------------------------------------------

        # Mock dates to have reproducible computed fields based on time
        self.reference_now = datetime(2021, 12, 1, 10, 0, 0)
        self.reference_today = datetime(2021, 12, 1)

        self.event_product = self.env['product.product'].create({
            'name': 'Test Event Registration',
            'default_code': 'EVENT_REG',
            'description_sale': 'Mighty Description',
            'list_price': 10,
            'standard_price': 30.0,
            'detailed_type': 'event',
        })

        self.event_tag_category_1 = self.env['event.tag.category'].create({
            'name': 'Type',
            'sequence': 2,
        })
        self.event_tag_category_1_tag_1 = self.env['event.tag'].create({
            'name': 'Online',
            'sequence': 10,
            'category_id': self.event_tag_category_1.id,
            'color': 8,
        })
        self.env['event.event'].search(
            [('name', 'like', '%Online Reveal%')]
        ).write(
            {'name': 'Do not click on me'}
        )
        self.event = self.env['event.event'].create({
            'name': 'Online Reveal TestEvent',
            'auto_confirm': True,
            'stage_id': self.env.ref('event.event_stage_booked').id,
            'address_id': False,
            'user_id': self.user_demo.id,
            'tag_ids': [(4, self.event_tag_category_1_tag_1.id)],
            # event if 8-18 in Europe/Brussels (DST) (first day: begins at 7, last day: ends at 17)
            'date_tz': 'Europe/Brussels',
            'date_begin': datetime.combine(self.reference_now, time(5, 0)) - timedelta(days=1),
            'date_end': datetime.combine(self.reference_now, time(15, 0)) + timedelta(days=1),
            # ticket informations
            'event_ticket_ids': [
                (0, 0, {
                    'name': 'Standard',
                    'product_id': self.event_product.id,
                    'price': 0,
                }), (0, 0, {
                    'name': 'VIP',
                    'product_id': self.event_product.id,
                    'seats_max': 10,
                })
            ],
            # activate menus
            'is_published': True,
            'website_menu': True,
            'website_track': True,
            'website_track_proposal': True,
            'exhibitor_menu': True,
            'community_menu': True,
        })

        self.event_customer = self.env['res.partner'].create({
            'name': 'Constantin Customer',
            'email': 'constantin@test.example.com',
            'country_id': self.env.ref('base.be').id,
            'phone': '0485112233',
            'mobile': False,
        })
        self.event_speaker = self.env['res.partner'].create({
            'name': 'Brandon Freeman',
            'email': 'brandon.freeman55@example.com',
            'phone': '(355)-687-3262',
        })

        # ------------------------------------------------------------
        # QUESTIONS
        # ------------------------------------------------------------

        self.event_question_1 = self.env['event.question'].create({
            'title': 'Which field are you working in',
            'question_type': 'simple_choice',
            'event_id': self.event.id,
            'once_per_order': False,
            'answer_ids': [
                (0, 0, {'name': 'Consumers'}),
                (0, 0, {'name': 'Sales'}),
                (0, 0, {'name': 'Research'}),
            ],
        })
        self.event_question_2 = self.env['event.question'].create({
            'title': 'How did you hear about us ?',
            'question_type': 'text_box',
            'event_id': self.event.id,
            'once_per_order': True,
        })

        # ------------------------------------------------------------
        # TRACKS
        # ------------------------------------------------------------

        self.track_0 = self.env['event.track'].create({
            'name': 'What This Event Is All About',
            'event_id': self.event.id,
            'stage_id': self.env.ref('website_event_track.event_track_stage3').id,
            'date': self.reference_now + timedelta(hours=1),
            'duration': 2,
            'is_published': True,
            'wishlisted_by_default': True,
            'user_id': self.user_admin.id,
            'partner_id': self.event_speaker.id,
        })
        self.track_1 = self.env['event.track'].create({
            'name': 'Live Testimonial',
            'event_id': self.event.id,
            'stage_id': self.env.ref('website_event_track.event_track_stage3').id,
            'date': self.reference_now - timedelta(minutes=30),
            'duration': 0.75,
            'is_published': True,
            'user_id': self.user_admin.id,
            'partner_id': self.event_speaker.id,
        })
        self.track_2 = self.env['event.track'].create({
            'name': 'Our Last Day Together !',
            'event_id': self.event.id,
            'stage_id': self.env.ref('website_event_track.event_track_stage3').id,
            'date': self.reference_now + timedelta(days=1),
            'duration': 0.75,
            'is_published': True,
            'user_id': self.user_admin.id,
            'partner_id': self.event_speaker.id,
        })

        # ------------------------------------------------------------
        # MEETING ROOMS
        # ----------------------------------------------------------

        self.env['event.meeting.room'].create({
            'name': 'Best wood for furniture',
            'summary': 'Let\'s talk about wood types for furniture',
            'target_audience': 'wood expert(s)',
            'is_pinned': True,
            'website_published': True,
            'event_id': self.event.id,
            'room_lang_id': self.env.ref('base.lang_en').id,
            'room_max_capacity': '12',
            'room_participant_count': 9,
        })

        self.env.flush_all()
