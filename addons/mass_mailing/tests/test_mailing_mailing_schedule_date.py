# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time

from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import users, Form
from odoo.tools import mute_logger


class TestMailingScheduleDateWizard(MassMailCommon, CronMixinCase):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('user_marketing')
    def test_mailing_next_departure(self):
        # test if mailing.mailing.next_departure is correctly set taking into account
        # presence of implicitly created cron triggers (since odoo v15). These should
        # launch cron job before its schedule nextcall datetime (if scheduled_date < nextcall)

        cron_job = self.env.ref('mass_mailing.ir_cron_mass_mailing_queue').sudo()
        cron_job.write({'nextcall' : datetime(2023, 2, 18, 9, 0)})
        cron_job_id = cron_job.id

        # case where user click on "Send" button (action_launch)
        with freeze_time(datetime(2023, 2, 17, 9, 0)):
            with self.capture_triggers(cron_job_id) as capt:
                mailing = self.env['mailing.mailing'].create({
                    'name': 'mailing',
                    'subject': 'some subject',
                    'mailing_model_id': self.env['ir.model']._get('res.partner').id,
                    'state' : 'draft'
                })
                mailing.action_launch()
            capt.records.ensure_one()

            # assert that the schedule_date and schedule_type fields are correct and that the mailing is put in queue
            self.assertEqual(mailing.next_departure, datetime(2023, 2, 17, 9, 0))
            self.assertIsNot(mailing.schedule_date, cron_job.nextcall)
            self.assertEqual(mailing.schedule_type, 'now')
            self.assertEqual(mailing.state, 'in_queue')
            self.assertEqual(capt.records.call_at, datetime(2023, 2, 17, 9, 0)) #verify that cron.trigger exists

        # case where client uses schedule wizard to chose a date between now and cron.job nextcall
        with freeze_time(datetime(2023, 2, 17, 9, 0)):
            with self.capture_triggers(cron_job_id) as capt:
                mailing = self.env['mailing.mailing'].create({
                    'name': 'mailing',
                    'subject': 'some subject',
                    'mailing_model_id': self.env['ir.model']._get('res.partner').id,
                    'state' : 'draft',
                    'schedule_date' : datetime(2023, 2, 17, 11, 0),
                    'schedule_type' : 'scheduled'
                })
                mailing.action_schedule()
            capt.records.ensure_one()

            self.assertEqual(mailing.schedule_date, datetime(2023, 2, 17, 11, 0))
            self.assertEqual(mailing.next_departure, datetime(2023, 2, 17, 11, 0))
            self.assertEqual(mailing.schedule_type, 'scheduled')
            self.assertEqual(mailing.state, 'in_queue')
            self.assertEqual(capt.records.call_at, datetime(2023, 2, 17, 11, 0)) #verify that cron.trigger exists

        # case where client uses schedule wizard to chose a date after cron.job nextcall
        # which means mails will get send after that date (datetime(2023, 2, 18, 9, 0))
        with freeze_time(datetime(2023, 2, 17, 9, 0)):
            with self.capture_triggers(cron_job_id) as capt:
                mailing = self.env['mailing.mailing'].create({
                    'name': 'mailing',
                    'subject': 'some subject',
                    'mailing_model_id': self.env['ir.model']._get('res.partner').id,
                    'state' : 'draft',
                    'schedule_date' : datetime(2024, 2, 17, 11, 0),
                    'schedule_type' : 'scheduled'
                })
                mailing.action_schedule()
            capt.records.ensure_one()

            self.assertEqual(mailing.schedule_date, datetime(2024, 2, 17, 11, 0))
            self.assertEqual(mailing.next_departure, datetime(2024, 2, 17, 11, 0))
            self.assertEqual(mailing.schedule_type, 'scheduled')
            self.assertEqual(mailing.state, 'in_queue')
            self.assertEqual(capt.records.call_at, datetime(2024, 2, 17, 11, 0)) #verify that cron.trigger exists

        # case where client uses schedule wizard to chose a date in the past
        with freeze_time(datetime(2023, 2, 17, 9, 0)):
            with self.capture_triggers(cron_job_id) as capt:
                mailing = self.env['mailing.mailing'].create({
                    'name': 'mailing',
                    'subject': 'some subject',
                    'mailing_model_id': self.env['ir.model']._get('res.partner').id,
                    'state' : 'draft',
                    'schedule_date' : datetime(2024, 2, 17, 11, 0),
                    'schedule_type' : 'scheduled'
                })
                # create a schedule date wizard
                # Have to use wizard for this case to simulate schedule date in the past
                # Otherwise "state" doesn't get update  from draft to'in_queue'
                # in test env vs production env (see mailing.mailing.schedule.date wizard)

                wizard_form = Form(
                    self.env['mailing.mailing.schedule.date'].with_context(default_mass_mailing_id=mailing.id))

                # set a schedule date
                wizard_form.schedule_date = datetime(2022, 2, 17, 11, 0)
                wizard = wizard_form.save()
                wizard.action_schedule_date()
            capt.records.ensure_one()

            self.assertEqual(mailing.schedule_date, datetime(2022, 2, 17, 11, 0))
            self.assertEqual(mailing.next_departure, datetime(2023, 2, 17, 9, 0)) #now
            self.assertEqual(mailing.schedule_type, 'scheduled')
            self.assertEqual(mailing.state, 'in_queue')
            self.assertEqual(capt.records.call_at, datetime(2022, 2, 17, 11, 0)) #verify that cron.trigger exists

    def test_mailing_schedule_date(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'mailing',
            'subject': 'some subject',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
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
