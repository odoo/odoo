# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from markupsafe import Markup

from .common import HelpdeskCommon
from odoo.exceptions import AccessError
from odoo.tests import Form
from odoo.tests.common import users


class TestHelpdeskFlow(HelpdeskCommon):
    """ Test used to check that the base functionalities of Helpdesk function as expected.
        - test_access_rights: tests a few access rights constraints
        - test_assign_close_dates: tests the assignation and closing time get computed correctly
        - test_ticket_partners: tests the number of tickets of a partner is computed correctly
        - test_team_assignation_[method]: tests the team assignation method work as expected
        - test_automatic_ticket_closing: tests automatic ticket closing after set number of days
    """

    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        ticket_model_id = cls.env['ir.model']._get_id('helpdesk.ticket')
        helpdesk_team_model_id = cls.env['ir.model']._get_id('helpdesk.team')

        cls.mail_alias = cls.env['mail.alias'].create({
            'alias_name': 'helpdesk_team',
            'alias_model_id': ticket_model_id,
            'alias_parent_model_id': helpdesk_team_model_id,
            'alias_parent_thread_id': cls.test_team.id,
            'alias_defaults': "{'team_id': %s}" % cls.test_team.id,
        })

        cls.email_to_alias_from = 'client_a@someprovider.com'
        cls.email_to_alias = """MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: blablabla1
Subject: helpdesk team 1 in company 1
From:  Client A <client_a@someprovider.com>
To: helpdesk_team@test.mycompany.com
Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

--000000000000a47519057e029630
Content-Type: text/plain; charset="UTF-8"


--000000000000a47519057e029630
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div>A good message ter</div>

--000000000000a47519057e029630--
"""
        return res

    def test_access_rights(self):
        # helpdesk user should only be able to:
        #   read: teams, stages, SLAs, ticket types
        #   read, create, write, unlink: tickets, tags
        # helpdesk manager:
        #   read, create, write, unlink: everything (from helpdesk)
        # we consider in these tests that if the user can do it, the manager can do it as well (as the group is implied)
        def test_write_and_unlink(record):
            record.write({'name': 'test_write'})
            record.unlink()

        def test_not_write_and_unlink(self, record):
            with self.assertRaises(AccessError):
                record.write({'name': 'test_write'})
            with self.assertRaises(AccessError):
                record.unlink()
            # self.assertRaises(AccessError, record.write({'name': 'test_write'})) # , "Helpdesk user should not be able to write on %s" % record._name)
            # self.assertRaises(AccessError, record.unlink(), "Helpdesk user could unlink %s" % record._name)

        # helpdesk.team access rights
        team = self.env['helpdesk.team'].with_user(self.helpdesk_manager).create({'name': 'test'})
        team.with_user(self.helpdesk_user).read()
        test_not_write_and_unlink(self, team.with_user(self.helpdesk_user))
        with self.assertRaises(AccessError):
            team.with_user(self.helpdesk_user).create({'name': 'test create'})
        test_write_and_unlink(team)

        # helpdesk.ticket access rights
        ticket = self.env['helpdesk.ticket'].with_user(self.helpdesk_user).create({'name': 'test'})
        ticket.read()
        test_write_and_unlink(ticket)

        # helpdesk.stage access rights
        stage = self.env['helpdesk.stage'].with_user(self.helpdesk_manager).create({
            'name': 'test',
            'team_ids': [(6, 0, [self.test_team.id])],
        })
        stage.with_user(self.helpdesk_user).read()
        test_not_write_and_unlink(self, stage.with_user(self.helpdesk_user))
        with self.assertRaises(AccessError):
            stage.with_user(self.helpdesk_user).create({
                'name': 'test create',
                'team_ids': [(6, 0, [self.test_team.id])],
            })
        test_write_and_unlink(stage)

        # helpdesk.sla access rights
        sla = self.env['helpdesk.sla'].with_user(self.helpdesk_manager).create({
            'name': 'test',
            'team_id': self.test_team.id,
            'stage_id': self.stage_done.id,
        })
        sla.with_user(self.helpdesk_user).read()
        test_not_write_and_unlink(self, sla.with_user(self.helpdesk_user))
        with self.assertRaises(AccessError):
            sla.with_user(self.helpdesk_user).create({
                'name': 'test create',
                'team_id': self.test_team.id,
                'stage_id': self.stage_done.id,
            })
        test_write_and_unlink(sla)

        # helpdesk.ticket.type access rights
        ticket_type = self.env['helpdesk.ticket.type'].with_user(self.helpdesk_manager).create({
            'name': 'test with unique name please',
        })
        ticket_type.with_user(self.helpdesk_user).read()
        test_not_write_and_unlink(self, ticket_type.with_user(self.helpdesk_user))
        with self.assertRaises(AccessError):
            ticket_type.with_user(self.helpdesk_user).create({
                'name': 'test create with unique name please',
            })
        test_write_and_unlink(ticket_type)

        # helpdesk.tag access rights
        tag = self.env['helpdesk.tag'].with_user(self.helpdesk_user).create({'name': 'test with unique name please'})
        tag.read()
        test_write_and_unlink(tag)

    def test_assign_close_dates(self):
        # helpdesk user create a ticket
        with self._ticket_patch_now('2019-01-08 12:00:00'):
            ticket1 = self.env['helpdesk.ticket'].with_user(self.helpdesk_user).create({
                'name': 'test ticket 1',
                'team_id': self.test_team.id,
            })

        with self._ticket_patch_now('2019-01-10 13:00:00'):
            # the helpdesk user takes the ticket
            ticket1.user_id = self.helpdesk_user
            # we verify the ticket is correctly assigned
            self.assertEqual(ticket1.user_id.id, ticket1._uid, "Assignation for ticket not correct")
            self.assertEqual(ticket1.assign_hours, 17, "Assignation time for ticket not correct")

        with self._ticket_patch_now('2019-01-10 15:00:00'):
            # we close the ticket and verify its closing time
            ticket1.write({'stage_id': self.stage_done.id})
            self.assertEqual(ticket1.close_hours, 19, "Close time for ticket not correct")

    def test_ticket_partners(self):
        # we create a partner
        partner = self.env['res.partner'].create({
            'name': 'Freddy Krueger'
        })
        # helpdesk user creates 2 tickets for the partner
        ticket1 = self.env['helpdesk.ticket'].with_user(self.helpdesk_user).create({
            'name': 'partner ticket 1',
            'team_id': self.test_team.id,
            'partner_id': partner.id,
        })
        self.env['helpdesk.ticket'].with_user(self.helpdesk_user).create({
            'name': 'partner ticket 2',
            'team_id': self.test_team.id,
            'partner_id': partner.id,
        })
        self.assertTrue(ticket1.partner_ticket_count == 1, "Incorrect number of tickets from the same partner.")

    def test_team_assignation_randomly(self):
        # we put the helpdesk user and manager in the test_team's members
        self.test_team.member_ids = [(6, 0, [self.helpdesk_user.id, self.helpdesk_manager.id])]
        # we set the assignation method to randomly (=uniformly distributed)
        self.test_team.update({'assign_method': 'randomly', 'auto_assignment': True})
        # we create a bunch of tickets
        for i in range(5):
            self.env['helpdesk.ticket'].create({
                'name': 'test ticket ' + str(i),
                'team_id': self.test_team.id,
            })
        # add unassigned ticket to test if the distribution is kept equal.
        self.env['helpdesk.ticket'].create({
            'name': 'ticket unassigned',
            'team_id': self.test_team.id,
            'user_id': False,
        })
        for i in range(5, 10):
            self.env['helpdesk.ticket'].create({
                'name': 'test ticket ' + str(i),
                'team_id': self.test_team.id,
            })
        # ensure both members have the same amount of tickets assigned
        self.assertEqual(self.env['helpdesk.ticket'].search_count([('user_id', '=', self.helpdesk_user.id)]), 5)
        self.assertEqual(self.env['helpdesk.ticket'].search_count([('user_id', '=', self.helpdesk_manager.id)]), 5)

    def test_team_assignation_balanced(self):
        # we put the helpdesk user and manager in the test_team's members
        self.test_team.member_ids = [(6, 0, [self.helpdesk_user.id, self.helpdesk_manager.id])]
        # we set the assignation method to randomly (=uniformly distributed)
        self.test_team.update({'assign_method': 'balanced', 'auto_assignment': True})
        # we create a bunch of tickets
        for i in range(4):
            self.env['helpdesk.ticket'].create({
                'name': 'test ticket ' + str(i),
                'team_id': self.test_team.id,
            })
        # ensure both members have the same amount of tickets assigned
        self.assertEqual(self.env['helpdesk.ticket'].search_count([('user_id', '=', self.helpdesk_user.id)]), 2)
        self.assertEqual(self.env['helpdesk.ticket'].search_count([('user_id', '=', self.helpdesk_manager.id)]), 2)

        # helpdesk user finishes his 2 tickets
        self.env['helpdesk.ticket'].search([('user_id', '=', self.helpdesk_user.id)]).write({'stage_id': self.stage_done.id})

        # we create 4 new tickets
        for i in range(4):
            self.env['helpdesk.ticket'].create({
                'name': 'test ticket ' + str(i),
                'team_id': self.test_team.id,
            })

        # ensure both members have the same amount of tickets assigned
        self.assertEqual(self.env['helpdesk.ticket'].search_count([('user_id', '=', self.helpdesk_user.id), ('close_date', '=', False)]), 3)
        self.assertEqual(self.env['helpdesk.ticket'].search_count([('user_id', '=', self.helpdesk_manager.id), ('close_date', '=', False)]), 3)

    def test_create_from_email_multicompany(self):
        company0 = self.env.company
        company1 = self.env['res.company'].create({'name': 'new_company0'})
        Partner = self.env['res.partner']

        self.env.user.write({
            'company_ids': [(4, company0.id, False), (4, company1.id, False)],
        })

        helpdesk_team_model = self.env['ir.model'].search([('model', '=', 'helpdesk_team')])
        ticket_model = self.env['ir.model'].search([('model', '=', 'helpdesk.ticket')])

        helpdesk_team0 = self.env['helpdesk.team'].create({
            'name': 'helpdesk team 0',
            'company_id': company0.id,
        })
        helpdesk_team1 = self.env['helpdesk.team'].create({
            'name': 'helpdesk team 1',
            'company_id': company1.id,
        })

        mail_alias0 = self.env['mail.alias'].create({
            'alias_name': 'helpdesk_team_0',
            'alias_model_id': ticket_model.id,
            'alias_parent_model_id': helpdesk_team_model.id,
            'alias_parent_thread_id': helpdesk_team0.id,
            'alias_defaults': "{'team_id': %s}" % helpdesk_team0.id,
        })
        mail_alias1 = self.env['mail.alias'].create({
            'alias_name': 'helpdesk_team_1',
            'alias_model_id': ticket_model.id,
            'alias_parent_model_id': helpdesk_team_model.id,
            'alias_parent_thread_id': helpdesk_team1.id,
            'alias_defaults': "{'team_id': %s}" % helpdesk_team1.id,
        })
        self.assertEqual((mail_alias0 + mail_alias1).alias_domain_id, self.mail_alias_domain)

        new_message0 = f"""MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: blablabla0
Subject: helpdesk team 0 in company 0
From:  A client <client_a@someprovider.com>
To: {mail_alias0.display_name}
Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

--000000000000a47519057e029630
Content-Type: text/plain; charset="UTF-8"


--000000000000a47519057e029630
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div>A good message</div>

--000000000000a47519057e029630--
"""

        new_message1 = f"""MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: blablabla1
Subject: helpdesk team 1 in company 1
From:  B client <client_b@someprovider.com>
To: {mail_alias1.display_name}
Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

--000000000000a47519057e029630
Content-Type: text/plain; charset="UTF-8"


--000000000000a47519057e029630
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div>A good message bis</div>

--000000000000a47519057e029630--
"""
        partners_exist = Partner.search([('email', 'in', ['client_a@someprovider.com', 'client_b@someprovider.com'])])
        self.assertFalse(partners_exist)

        helpdesk_ticket0_id = self.env['mail.thread'].message_process(False, new_message0)
        helpdesk_ticket1_id = self.env['mail.thread'].message_process(False, new_message1)
        self.env.cr.flush()  # trigger pre-commit
        helpdesk_ticket0 = self.env['helpdesk.ticket'].browse(helpdesk_ticket0_id)
        helpdesk_ticket1 = self.env['helpdesk.ticket'].browse(helpdesk_ticket1_id)

        self.assertEqual(helpdesk_ticket0.team_id, helpdesk_team0)
        self.assertEqual(helpdesk_ticket1.team_id, helpdesk_team1)

        self.assertEqual(helpdesk_ticket0.company_id, company0)
        self.assertEqual(helpdesk_ticket1.company_id, company1)

        partner0 = Partner.search([('email', '=', 'client_a@someprovider.com')])
        partner1 = Partner.search([('email', '=', 'client_b@someprovider.com')])
        self.assertTrue(partner0)
        self.assertTrue(partner1)

        self.assertEqual(partner0.company_id, company0)
        self.assertEqual(partner1.company_id, company1)

        self.assertEqual(partner0.name, "A client")
        self.assertEqual(partner1.name, "B client")

        self.assertEqual(helpdesk_ticket0.partner_id, partner0)
        self.assertEqual(helpdesk_ticket1.partner_id, partner1)

        self.assertTrue(partner0 in helpdesk_ticket0.message_follower_ids.mapped('partner_id'))
        self.assertTrue(partner1 in helpdesk_ticket1.message_follower_ids.mapped('partner_id'))

    def test_ticket_sequence_created_from_multi_company(self):
        """
        In this test we ensure that in a multi-company environment, mail sent to helpdesk team
        create a ticket with the right sequence.
        """
        company0 = self.env.company
        company1 = self.env['res.company'].create({'name': 'new_company0'})

        self.env.user.write({
            'company_ids': [(4, company0.id, False), (4, company1.id, False)],
        })

        helpdesk_team_model = self.env['ir.model'].search([('model', '=', 'helpdesk_team')])
        ticket_model = self.env['ir.model'].search([('model', '=', 'helpdesk.ticket')])

        helpdesk_team0 = self.env['helpdesk.team'].create({
            'name': 'helpdesk team 0',
            'company_id': company0.id,
        })
        helpdesk_team1 = self.env['helpdesk.team'].create({
            'name': 'helpdesk team 1',
            'company_id': company1.id,
        })

        _mail_alias_0, mail_alias_1 = self.env['mail.alias'].create([
            {
                'alias_name': 'helpdesk_team_0',
                'alias_model_id': ticket_model.id,
                'alias_parent_model_id': helpdesk_team_model.id,
                'alias_parent_thread_id': helpdesk_team0.id,
                'alias_defaults': "{'team_id': %s}" % helpdesk_team0.id,
            },
            {
                'alias_name': 'helpdesk_team_1',
                'alias_model_id': ticket_model.id,
                'alias_parent_model_id': helpdesk_team_model.id,
                'alias_parent_thread_id': helpdesk_team1.id,
                'alias_defaults': "{'team_id': %s}" % helpdesk_team1.id,
            }
        ])

        new_message1 = f"""MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: blablabla1
Subject: helpdesk team 1 in company 1
From:  B client <client_b@someprovider.com>
To: {mail_alias_1.display_name}
Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

--000000000000a47519057e029630
Content-Type: text/plain; charset="UTF-8"


--000000000000a47519057e029630
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div>A good message bis</div>

--000000000000a47519057e029630--
"""
        self.env['ir.sequence'].create([
            {
                'company_id': company0.id,
                'name': 'test-sequence-00',
                'prefix': 'FirstCompany',
                'code': 'helpdesk.ticket'
            },
            {
                'company_id': company1.id,
                'name': 'test-sequence-01',
                'prefix': 'SecondCompany',
                'code': 'helpdesk.ticket'
            }
        ])

        helpdesk_ticket1_id = self.env['mail.thread'].message_process('helpdesk.ticket', new_message1)
        helpdesk_ticket1 = self.env['helpdesk.ticket'].browse(helpdesk_ticket1_id)
        self.assertTrue(helpdesk_ticket1.ticket_ref.startswith('SecondCompany'))

    def test_email_non_ascii(self):
        """
        Ensure that non-ascii characters are correctly handled in partner email addresses
        """
        new_message = """MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: blablabla1
Subject: helpdesk team 1 in company 1
From:  Client with a §tràÑge name <client_b@someprovaîdère.com>
To: helpdesk_team@test.mycompany.com
Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

--000000000000a47519057e029630
Content-Type: text/plain; charset="UTF-8"


--000000000000a47519057e029630
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

<div>A good message ter</div>

--000000000000a47519057e029630--
"""
        helpdesk_ticket = self.env['mail.thread'].message_process('helpdesk.ticket', new_message)
        helpdesk_ticket = self.env['helpdesk.ticket'].browse(helpdesk_ticket)

        self.assertEqual(helpdesk_ticket.partner_id.name, "Client with a §tràÑge name")
        self.assertEqual(helpdesk_ticket.partner_id.email, "client_b@someprovaîdère.com")
        self.assertEqual(helpdesk_ticket.partner_email, "client_b@someprovaîdère.com")

    def test_email_without_mail_template(self):
        """
        A mail sent to the alias without mail template on the stage should also create a partner
        """
        stage = self.test_team._determine_stage()[self.test_team.id]
        stage.template_id = False

        helpdesk_ticket = self.env['mail.thread'].message_process('helpdesk.ticket', self.email_to_alias)
        helpdesk_ticket = self.env['helpdesk.ticket'].browse(helpdesk_ticket)

        self.assertEqual(helpdesk_ticket.partner_id.name, "Client A")

    def test_email_with_mail_template_portal_user(self):
        """
        Portal users receive an email when they create a ticket
        """
        self.stage_new.template_id = self.env.ref('helpdesk.new_ticket_request_email_template')
        self.helpdesk_portal.email = self.email_to_alias_from

        helpdesk_ticket = self.env['mail.thread'].message_process('helpdesk.ticket', self.email_to_alias)
        helpdesk_ticket = self.env['helpdesk.ticket'].browse(helpdesk_ticket)
        self.assertEqual(helpdesk_ticket.partner_id, self.helpdesk_portal.partner_id)

        self.flush_tracking()

        # check that when a portal user creates a ticket there is two message on the ticket:
        # - the creation message note
        # - the mail from the stage mail template
        template_msg, creation_log = helpdesk_ticket.message_ids
        self.assertEqual(template_msg.subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(creation_log.subtype_id, self.env.ref('helpdesk.mt_ticket_new'))

    def test_email_with_mail_template_internal_user(self):
        """
        Internal users receive an email when they create a ticket by email.
        """
        self.stage_new.template_id = self.env.ref('helpdesk.new_ticket_request_email_template')
        self.helpdesk_user.email = self.email_to_alias_from

        helpdesk_ticket = self.env['mail.thread'].message_process('helpdesk.ticket', self.email_to_alias)
        helpdesk_ticket = self.env['helpdesk.ticket'].browse(helpdesk_ticket)
        self.assertEqual(helpdesk_ticket.partner_id, self.helpdesk_user.partner_id)

        self.flush_tracking()

        # check that when an internal user creates a ticket there is two messages on the ticket:
        # - the creation message note
        # - the mail from the stage mail template
        template_msg, creation_log = helpdesk_ticket.message_ids
        self.assertEqual(template_msg.subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(creation_log.subtype_id, self.env.ref('helpdesk.mt_ticket_new'))

    def test_team_assignation_balanced_sla(self):
        #We create an sla policy with minimum priority set as '2'
        self.test_team.use_sla = True
        sla = self.env['helpdesk.sla'].create({
            'name': 'test sla policy',
            'team_id': self.test_team.id,
            'stage_id': self.stage_progress.id,
            'priority': '2',
            'time': 1,
        })

        #We create a ticket with priority less than what's on the sla policy
        ticket_1 = self.env['helpdesk.ticket'].create({
            'name': 'test ',
            'team_id': self.test_team.id,
            'priority': '1'
        })

        #We create a ticket with priority equal to what's on the sla policy
        ticket_2 = self.env['helpdesk.ticket'].create({
            'name': 'test sla ticket',
            'team_id': self.test_team.id,
            'priority': '2'
        })

        #We create a ticket with priority greater than what's on the sla policy
        ticket_3 = self.env['helpdesk.ticket'].create({
            'name': 'test sla ticket',
            'team_id': self.test_team.id,
            'priority': '3'
        })
        #We confirm that the sla policy has been applied successfully on the ticket.
        #sla policy must not be applied
        self.assertTrue(sla not in ticket_1.sla_status_ids.mapped('sla_id'))
        self.assertTrue(sla not in ticket_3.sla_status_ids.mapped('sla_id'))
        #sla policy must be applied
        self.assertTrue(sla in ticket_2.sla_status_ids.mapped('sla_id'))

    def test_automatic_ticket_closing(self):
        self.test_team.write({
            'auto_close_ticket': True,
            'auto_close_day': 7,
            'to_stage_id': self.stage_cancel.id,
        })

        create_ticket = lambda stage_id: self.env['helpdesk.ticket'].create({
            'name': 'Ticket 1',
            'team_id': self.test_team.id,
            'stage_id': stage_id,
        })

        ticket_1 = create_ticket(self.stage_new.id)
        ticket_2 = create_ticket(self.stage_progress.id)
        ticket_3 = create_ticket(self.stage_done.id)

        with freeze_time(datetime.now() + relativedelta(days=10)):
            self.test_team._cron_auto_close_tickets()

        # With no from_stage_ids, all tickets from non closing stages should be moved
        self.assertEqual(ticket_1.stage_id, self.stage_cancel)
        self.assertEqual(ticket_2.stage_id, self.stage_cancel)
        self.assertEqual(ticket_3.stage_id, self.stage_done)

        self.test_team.from_stage_ids |= self.stage_progress
        ticket_4 = create_ticket(self.stage_new.id)
        ticket_5 = create_ticket(self.stage_progress.id)
        ticket_6 = create_ticket(self.stage_done.id)

        with freeze_time(datetime.now() + relativedelta(days=10)):
            self.test_team._cron_auto_close_tickets()

        # Only tasks in the stages in from_stage_ids should be moved
        self.assertEqual(ticket_4.stage_id, self.stage_new)
        self.assertEqual(ticket_5.stage_id, self.stage_cancel)
        self.assertEqual(ticket_6.stage_id, self.stage_done)

        ticket_7 = create_ticket(self.stage_progress.id)

        with freeze_time(datetime.now() + relativedelta(days=5)):
            self.test_team._cron_auto_close_tickets()

        # Tickets under the threshold should not be moved (5 < 7)
        self.assertEqual(ticket_7.stage_id, self.stage_progress)

    def test_create_from_email(self):
        with freeze_time('2018-12-27 00:00:00'):
            helpdesk_ticket = self.env['helpdesk.ticket'].create({'name': 'Hi! How was your day?'})

        customer_partner = self.env['res.partner'].create({'name': 'Luc Mélanchetout'})
        helpdesk_partner = self.helpdesk_user.partner_id

        # hours utc to fit in 08:00 - 17:00 belgian calendar
        hours_and_authors = [
            ('08', customer_partner),
            ('09', helpdesk_partner),   #   2h since creation (= first_response_hours)
            ('10', helpdesk_partner),
            ('11', customer_partner),
            ('12', customer_partner),
            ('14', helpdesk_partner),   # + 2h since last customer's message (3h - 1h break)
            ('15', customer_partner),
            ('16', helpdesk_partner),   # + 1h since last customer's message
        ]                               # -----
                                        # = 5h /3responses = 1.67h /response (= avg_response_hours)
        comment_subtype = self.env.ref('mail.mt_comment')
        email_vals = {
            'model': 'helpdesk.ticket',
            'res_id': helpdesk_ticket.id,
            'body': 'Good, you?',
            'subtype_id': comment_subtype.id,
        }
        email_vals_list = []
        for hour, author in hours_and_authors:
            temp_email_vals = email_vals.copy()
            temp_email_vals.update({
                'author_id': author.id,
                'date': '2018-12-27 %s:00:00' % hour,
            })
            email_vals_list.append(temp_email_vals)
        helpdesk_ticket.website_message_ids = self.env['mail.message'].create(email_vals_list)
        self.assertEqual(helpdesk_ticket.first_response_hours, 2.0)
        self.assertEqual(helpdesk_ticket.avg_response_hours, 5 / 3)

    def test_ticket_count_according_to_partner(self):
        # 1) create a partner
        partner = self.env['res.partner'].create({
            'name': 'Freddy Krueger'
        })

        # 2) create one open and one closed ticket
        open_ticket, closed_ticket = self.env['helpdesk.ticket'].with_user(self.helpdesk_user).create([{
            'name': 'open ticket',
            'team_id': self.test_team.id,
            'partner_id': partner.id,
        }, {
            'name': 'solved ticket',
            'team_id': self.test_team.id,
            'partner_id': partner.id,
            'stage_id': self.stage_done.id,
        }])

        # 3) check ticket count according to partner ticket
        self.assertEqual(open_ticket.partner_open_ticket_count, 0, "There should be no other open ticket than this one for this partner")
        self.assertEqual(open_ticket.partner_ticket_count, 1, "There should be one other ticket than this one for this partner")
        self.assertEqual(closed_ticket.partner_open_ticket_count, 1, "There should be one other open ticket than this one for this partner")
        self.assertEqual(closed_ticket.partner_ticket_count, 1, "There should be one other ticket than this one for this partner")

    @users('hm')
    def test_helpdesk_team_members_fallback(self):
        helpdesk_form = Form(self.env['helpdesk.team'])
        helpdesk_form.name = 'test team 2'
        helpdesk_form.auto_assignment = True
        helpdesk_form.member_ids.clear()
        helpdesk_form.auto_assignment = False
        helpdesk = helpdesk_form.save()

        self.assertEqual(helpdesk.member_ids, self.env.user)

    def test_create_from_email_new_customer_ticket_description(self):
        Partner = self.env['res.partner']

        new_message = """MIME-Version: 1.0
Date: Thu, 27 Dec 2018 16:27:45 +0100
Message-ID: blablabla0
Subject: new customer
From:  A client <client_a@someprovider.com>
To: helpdesk_team@aqualung.com
Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

--000000000000a47519057e029630
Content-Type: text/plain; charset="UTF-8"


--000000000000a47519057e029630
Content-Type: text/html; charset="UTF-8"
Content-Transfer-Encoding: quoted-printable

should be in the ticket's description

--000000000000a47519057e029630--
"""

        partner_exist = Partner.search([('email', 'in', ['client_a@someprovider.com'])])
        self.assertFalse(partner_exist, "Partner should not exist")

        helpdesk_ticket_id = self.env['mail.thread'].message_process('helpdesk.ticket', new_message)
        helpdesk_ticket = self.env['helpdesk.ticket'].browse(helpdesk_ticket_id)

        partner = Partner.search([('email', '=', 'client_a@someprovider.com')])
        self.assertTrue(partner, "Partner should be created")

        self.assertEqual(helpdesk_ticket.partner_id, partner)

        self.assertEqual(helpdesk_ticket.description, Markup("<p>should be in the ticket's description\n</p>"), "the email body should be in the ticket's description")

    def test_create_from_internal_for_internal(self):
        """
        Test that we can create a ticket from an internal user for an internal user, without raising any access error.
        Also test that empty phone number doesn't overwrite the partner's phone number.
        """
        user = self.env['res.users'].create({
            'name': 'User',
            'login': 'user',
            'email': 'user@user.com',
            'groups_id': [(6, 0, [self.env.ref('helpdesk.group_helpdesk_manager').id,
                        self.env.ref('base.group_partner_manager').id])],
        })

        self.assertFalse(self.helpdesk_user.partner_id.phone)
        ticket = self.env['helpdesk.ticket'].with_user(user).create({
            'name': 'test ticket 1',
            'team_id': self.test_team.id,
            'partner_id': self.helpdesk_user.partner_id.id,
            'partner_phone': '123'
        })
        self.assertEqual(self.helpdesk_user.partner_id.phone, ticket.partner_phone)
        ticket = self.env['helpdesk.ticket'].with_user(self.helpdesk_user).create({
            'name': 'test ticket 2',
            'team_id': self.test_team.id,
            'partner_id': self.helpdesk_user.partner_id.id,
            'partner_phone': ''
        })
        self.assertEqual(self.helpdesk_user.partner_id.phone, '123')
