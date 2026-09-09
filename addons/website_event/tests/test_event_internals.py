from datetime import datetime, timedelta

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.fields import Datetime as FieldsDatetime
from odoo.tests.common import users

from odoo.addons.event.tests.common import EventCase
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website.tests.test_website_visitor import MockVisitor
from odoo.addons.website_event.controllers.main import WebsiteEventController


class TestEventData(EventCase, MockVisitor):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event_public, cls.event_link_only, cls.event_logged_users = (
            cls.env["event.event"]
            .sudo()
            .create(
                [
                    {
                        "name": "event",
                        "website_visibility": website_visibility,
                        "website_published": True,
                    }
                    for website_visibility in ["public", "link", "logged_users"]
                ]
            )
        )
        cls.events_visibility_test = (
            cls.event_public | cls.event_link_only | cls.event_logged_users
        )

    def test_process_attendees_form(self):
        event = self.env["event.event"].create(
            {
                "name": "Event Update Type",
                "event_type_id": self.event_type_questions.with_user(self.env.user).id,
                "date_begin": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
            }
        )
        ticket_id_1 = self.env["event.event.ticket"].create(
            [
                {
                    "name": "Regular",
                    "event_id": event.id,
                    "seats_max": 200,
                }
            ]
        )
        ticket_id_2 = self.env["event.event.ticket"].create(
            [
                {
                    "name": "VIP",
                    "event_id": event.id,
                    "seats_max": 200,
                }
            ]
        )

        [name_question, email_question, phone_question] = event.question_ids.filtered(
            lambda q: q.question_type in ("name", "email", "phone", "company_name")
        )

        [second_phone_question, company_name_question] = self.env[
            "event.question"
        ].create(
            [
                {
                    "title": "Second Phone",
                    "question_type": "phone",
                    "event_ids": [Command.set(event.ids)],
                },
                {
                    "title": "Company Name",
                    "question_type": "company_name",
                    "event_ids": [Command.set(event.ids)],
                },
            ]
        )

        form_details = {
            "1-name-%s" % name_question.id: "Pixis",
            "1-email-%s" % email_question.id: "pixis@gmail.com",
            "1-phone-%s" % phone_question.id: "+32444444444",
            "1-phone-%s" % second_phone_question.id: "+32555555555",
            "1-event_ticket_id": ticket_id_1.id,
            "2-name-%s" % name_question.id: "Geluchat",
            "2-email-%s" % email_question.id: "geluchat@gmail.com",
            "2-phone-%s" % phone_question.id: "+32777777777",
            "2-company_name-%s" % company_name_question.id: "My Company",
            "2-event_ticket_id": ticket_id_2.id,
            "1-simple_choice-%s" % self.event_question_1.id: "5",
            "2-simple_choice-%s" % self.event_question_1.id: "9",
            "0-simple_choice-%s" % self.event_question_2.id: "7",
            "0-text_box-%s" % self.event_question_3.id: "Free Text",
            "custom-field": "custom-value",
            "recaptcha_token_response": "opaquetokenvalue",
        }

        with MockRequest(self.env):
            registrations = WebsiteEventController()._process_attendees_form(
                event, form_details
            )

        self.assertEqual(
            registrations,
            [
                {
                    "name": "Pixis",
                    "email": "pixis@gmail.com",
                    "phone_ids": [
                        Command.create({"number": "+32444444444", "type": "mobile"})
                    ],
                    "event_ticket_id": ticket_id_1.id,
                    "registration_answer_ids": [
                        (
                            0,
                            0,
                            {
                                "question_id": name_question.id,
                                "value_text_box": "Pixis",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": email_question.id,
                                "value_text_box": "pixis@gmail.com",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": phone_question.id,
                                "value_text_box": "+32444444444",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": second_phone_question.id,
                                "value_text_box": "+32555555555",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": self.event_question_1.id,
                                "value_answer_id": 5,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": self.event_question_2.id,
                                "value_answer_id": 7,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": self.event_question_3.id,
                                "value_text_box": "Free Text",
                            },
                        ),
                    ],
                },
                {
                    "name": "Geluchat",
                    "email": "geluchat@gmail.com",
                    "phone_ids": [
                        Command.create({"number": "+32777777777", "type": "mobile"})
                    ],
                    "company_name": "My Company",
                    "event_ticket_id": ticket_id_2.id,
                    "registration_answer_ids": [
                        (
                            0,
                            0,
                            {
                                "question_id": name_question.id,
                                "value_text_box": "Geluchat",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": email_question.id,
                                "value_text_box": "geluchat@gmail.com",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": phone_question.id,
                                "value_text_box": "+32777777777",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": company_name_question.id,
                                "value_text_box": "My Company",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": self.event_question_1.id,
                                "value_answer_id": 9,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": self.event_question_2.id,
                                "value_answer_id": 7,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": self.event_question_3.id,
                                "value_text_box": "Free Text",
                            },
                        ),
                    ],
                },
            ],
        )

    def test_process_attendees_form_no_tickets(self):
        event = self.env["event.event"].create(
            {
                "name": "Test Event",
                "event_type_id": self.event_type_questions.id,
                "date_begin": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
            }
        )

        name_question, email_question = event.question_ids.filtered(
            lambda q: q.question_type in ("name", "email")
        )

        form_details = {
            "1-name-%s" % name_question.id: "Attendee Name",
            "1-email-%s" % email_question.id: "attendee@example.com",
            "1-event_ticket_id": "0",
        }

        with MockRequest(self.env):
            registrations = WebsiteEventController()._process_attendees_form(
                event, form_details
            )

        self.assertEqual(len(registrations), 1)
        self.assertDictEqual(
            registrations[0],
            {
                "name": "Attendee Name",
                "email": "attendee@example.com",
                "event_ticket_id": False,
                "registration_answer_ids": [
                    (
                        0,
                        0,
                        {
                            "question_id": name_question.id,
                            "value_text_box": "Attendee Name",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "question_id": email_question.id,
                            "value_text_box": "attendee@example.com",
                        },
                    ),
                ],
            },
        )
        self.assertTrue(
            registrations[0]["event_ticket_id"] is False,
            f"Falsy string ids should be False, not {registrations[0]['event_ticket_id']}",
        )

    def test_process_attendees_form_missing_ticket_key(self):
        """A POST that never sends the '<idx>-event_ticket_id' key at all (as
        opposed to sending it empty/falsy) must not silently produce a
        registration with a missing 'event_ticket_id' key that would later
        crash a bare dict subscript in registration_confirm()."""
        event = self.env["event.event"].create(
            {
                "name": "Test Event",
                "event_type_id": self.event_type_questions.id,
                "date_begin": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
            }
        )

        name_question, email_question = event.question_ids.filtered(
            lambda q: q.question_type in ("name", "email")
        )

        form_details = {
            "1-name-%s" % name_question.id: "Attendee Name",
            "1-email-%s" % email_question.id: "attendee@example.com",
        }

        with MockRequest(self.env):
            registrations = WebsiteEventController()._process_attendees_form(
                event, form_details
            )

        self.assertEqual(len(registrations), 1)
        self.assertNotIn(
            "event_ticket_id",
            registrations[0],
            "A registration missing its ticket key must stay detectable "
            "downstream, not silently default to a key that isn't there.",
        )

    def test_check_posted_ids_are_offered_slot(self):
        """A posted event_slot_id that doesn't belong to the event must raise
        a friendly UserError (caught by the framework as a normal error page)
        instead of reaching event.slot's model-level ValidationError."""
        event = self.env["event.event"].create(
            {
                "name": "Test Event",
                "event_type_id": self.event_type_questions.id,
                "date_begin": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
            }
        )
        other_event = self.env["event.event"].create(
            {
                "name": "Other Event",
                "date_begin": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
            }
        )
        self.env["event.slot"].create(
            {
                "event_id": event.id,
                "date": datetime.today() + timedelta(days=2),
                "start_hour": 9.0,
                "end_hour": 10.0,
            }
        )
        foreign_slot = self.env["event.slot"].create(
            {
                "event_id": other_event.id,
                "date": datetime.today() + timedelta(days=2),
                "start_hour": 9.0,
                "end_hour": 10.0,
            }
        )

        with MockRequest(self.env), self.assertRaises(UserError):
            WebsiteEventController()._check_posted_ids_are_offered(
                {"1-event_slot_id": str(foreign_slot.id)},
                "event_slot_id",
                event.event_slot_ids.ids,
                "This slot is not available for this event",
            )

    def test_process_tickets_form_negative_quantity(self):
        """A posted 'nb_register-<id>' value that is zero or negative must be
        dropped, not returned as an order with a negative/zero quantity that
        would understate the displayed ordered_seats count."""
        event = self.env["event.event"].create(
            {
                "name": "Test Event",
                "date_begin": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
            }
        )
        ticket = self.env["event.event.ticket"].create(
            {
                "name": "Regular",
                "event_id": event.id,
                "seats_max": 200,
            }
        )

        with MockRequest(self.env):
            tickets = WebsiteEventController()._process_tickets_form(
                event, {"nb_register-%s" % ticket.id: "-5"}
            )

        self.assertEqual(
            tickets,
            [],
            "A negative registration count must not produce a ticket order.",
        )

    def test_filter_open_slots_query_count(self):
        """_filter_open_slots must batch seat-availability lookups per
        EVENT, not per slot: the query count for filtering N slots on one
        event must not grow with N."""
        event = self.env["event.event"].create(
            {
                "name": "Multi-slot event",
                "date_begin": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
            }
        )
        one_slot = self.env["event.slot"].create(
            {
                "event_id": event.id,
                "date": datetime.today() + timedelta(days=2),
                "start_hour": 9.0,
                "end_hour": 10.0,
            }
        )
        more_slots = self.env["event.slot"].create(
            [
                {
                    "event_id": event.id,
                    "date": datetime.today() + timedelta(days=hour),
                    "start_hour": 9.0,
                    "end_hour": 10.0,
                }
                for hour in range(3, 7)
            ]
        )

        self.env.invalidate_all()
        self.env.flush_all()
        count0 = self.env.cr.sql_statement_count
        one_slot._filter_open_slots()
        queries_for_one = self.env.cr.sql_statement_count - count0

        self.env.invalidate_all()
        self.env.flush_all()
        count0 = self.env.cr.sql_statement_count
        (one_slot | more_slots)._filter_open_slots()
        queries_for_five = self.env.cr.sql_statement_count - count0

        self.assertEqual(
            queries_for_one,
            queries_for_five,
            "Filtering 5 slots on the same event must cost the same "
            "number of queries as filtering 1 - one availability lookup "
            "per event, not per slot.",
        )

    def test_registration_answer_search(self):

        event = self.env["event.event"].create(
            {
                "name": "Test Event",
                "event_type_id": self.event_type_questions.id,
                "date_begin": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
            }
        )

        [registration_1, registration_2, registration_3] = self.env[
            "event.registration"
        ].create(
            [
                {
                    "event_id": event.id,
                    "partner_id": self.env.user.partner_id.id,
                    "registration_answer_ids": [
                        (
                            0,
                            0,
                            {
                                "question_id": self.event_question_1.id,
                                "value_answer_id": self.event_question_1.answer_ids[
                                    0
                                ].id,
                            },
                        ),
                    ],
                },
                {
                    "event_id": event.id,
                    "partner_id": self.env.user.partner_id.id,
                    "registration_answer_ids": [
                        (
                            0,
                            0,
                            {
                                "question_id": self.event_question_1.id,
                                "value_answer_id": self.event_question_1.answer_ids[
                                    1
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "question_id": self.event_question_3.id,
                                "value_text_box": "My Answer",
                            },
                        ),
                    ],
                },
                {
                    "event_id": event.id,
                    "partner_id": self.env.user.partner_id.id,
                    "registration_answer_ids": [
                        (
                            0,
                            0,
                            {
                                "question_id": self.event_question_3.id,
                                "value_text_box": "Answer2",
                            },
                        ),
                    ],
                },
            ]
        )

        search_res = self.env["event.registration"].search(
            [("registration_answer_ids", "ilike", "Answer1")]
        )
        self.assertEqual(search_res, registration_1)

        search_res = self.env["event.registration"].search(
            [("registration_answer_ids", "ilike", "Answer2")]
        )
        self.assertEqual(search_res, registration_2 | registration_3)

    @users("user_employee")
    def test_website_visibility_internal_user(self):
        visible_events = self.env["event.event"].search(
            [
                ("id", "in", self.events_visibility_test.ids),
                ("is_visible_on_website", "=", True),
            ]
        )
        self.assertIn(self.event_public, visible_events)
        self.assertNotIn(self.event_link_only, visible_events)
        self.assertIn(self.event_logged_users, visible_events)

    @users("portal_test")
    def test_website_visibility_portal_user(self):
        visible_events = self.env["event.event"].search(
            [
                ("id", "in", self.events_visibility_test.ids),
                ("is_visible_on_website", "=", True),
            ]
        )
        self.assertIn(self.event_public, visible_events)
        self.assertNotIn(self.event_link_only, visible_events)
        self.assertIn(self.event_logged_users, visible_events)

    @users("portal_test")
    def test_website_visibility_portal_user_unrelated_registration(self):
        """A logged-in user with no visitor must only be considered
        participating in events tied to their OWN partner, never in every
        event that happens to have any registration at all (WEE-01: the
        heuristic must seed with Domain.FALSE, not Domain.TRUE)."""
        other_partner = self.env["res.partner"].sudo().create({"name": "Someone Else"})
        self.env["event.registration"].sudo().create(
            {
                "name": "Unrelated registration",
                "event_id": self.event_link_only.id,
                "partner_id": other_partner.id,
                "state": "open",
            }
        )

        visible_events = self.env["event.event"].search(
            [
                ("id", "in", self.events_visibility_test.ids),
                ("is_visible_on_website", "=", True),
            ]
        )
        self.assertNotIn(
            self.event_link_only,
            visible_events,
            "An unrelated partner's registration must not make this event "
            "participating for the current user.",
        )

    @users("public_test")
    def test_website_visibility_public_user(self):
        visible_events = self.env["event.event"].search(
            [
                ("id", "in", self.events_visibility_test.ids),
                ("is_visible_on_website", "=", True),
            ]
        )
        self.assertIn(self.event_public, visible_events)
        self.assertNotIn(self.event_link_only, visible_events)
        self.assertNotIn(self.event_logged_users, visible_events)

        website_visitor = (
            self.env["website.visitor"]
            .sudo()
            .create(
                {
                    "name": "Website Visitor",
                    "access_token": "c8d20bd006c3bf46b875451defb5991d",
                }
            )
        )
        self.env["event.registration"].sudo().create(
            {
                "name": "Registration from visitor",
                "event_id": self.event_link_only.id,
                "visitor_id": website_visitor.id,
            }
        )
        with self.mock_visitor_from_request(force_visitor=website_visitor):
            visible_events = self.env["event.event"].search(
                [
                    ("id", "in", self.events_visibility_test.ids),
                    ("is_visible_on_website", "=", True),
                ]
            )
            self.assertIn(self.event_public, visible_events)
            self.assertIn(
                self.event_link_only,
                visible_events,
                "Should now be visible because visitor is participating",
            )
            self.assertNotIn(self.event_logged_users, visible_events)
