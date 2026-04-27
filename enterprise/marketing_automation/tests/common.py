# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from contextlib import contextmanager
from freezegun import freeze_time
from unittest.mock import patch

from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mass_mailing.tests.common import MassMailCase, MassMailCommon

_logger = logging.getLogger(__name__)


class MarketingAutomationCase(MassMailCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # store MA crons on cls, always handy to have them available without ref
        cls.cron_ma_sync_participants = cls.env.ref('marketing_automation.ir_cron_campaign_sync_participants')
        cls.cron_ma_execute_activities = cls.env.ref('marketing_automation.ir_cron_campaign_execute_activities')

    @contextmanager
    def mock_datetime_and_now(self, mock_dt):
        """ Used when synchronization date (using env.cr.now()) is important
        in addition to standard datetime mocks. Used mainly to detect sync
        issues. """
        with freeze_time(mock_dt), \
             patch.object(self.env.cr, 'now', lambda: mock_dt):
            yield

    # ------------------------------------------------------------
    # TOOLS AND ASSERTS
    # ------------------------------------------------------------

    def assertMarketAutoTraces(self, participants_info, activity, strict=True, canceled_res_ids=None, **trace_values):
        """ Check content of traces.

        :param participants_info: [{
            # participants
            'participants': participants record_set,      # optional: allow to check coherency of expected participants
            'status': status,                             # marketing trace status (processed, ...) for all records
            # record info
            'records': records,                           # records going through this activity
            'records_to_partner: {rec.id: <res.partner>}  # linked partner (recipient)
            'records_to_status: {rec.id: status}          # record-specific override of 'status'
            # marketing trace
            'fields_values': dict                         # optional fields values to check on marketing.trace
            # mailing/sms trace
            'trace_author': author of mail/sms            # used notably to ease finding emails / sms
            'trace_content': content of mail/sms          # content of sent mail / sms / whatsapp
            'trace_email': email logged on trace          # may differ from 'email_normalized'
            'trace_email_to_mail': email logged on mail   # for assertMailMail
            'trace_email_to_recipients': email            # for assertSentEmail
            'trace_failure_type': failure_type of trace   # to check status update in case of failure
            'trace_status': status of mailing trace,      # if not set: check there is no mailing trace
            'mail_values': mail.mail check                # for assertMailMail
        }, {}, ... ]
        :param activity: a marketing.activity on which marketing traces are about
            to be checked, as well as sub records like mailing.trace if requested
            by status;
        :param strict: whether activity traces must match given records IDs;
        :param canceled_res_ids: quick check for canceled marketing traces not given
            in participants_info (e.g. unlinked records, quick validation, ...);
        """
        all_records = self.env[activity.campaign_id.model_name]
        for info in participants_info:
            all_records += info['records']

        # find traces linked to activity, ensure we have one trace / record
        traces = self.env['marketing.trace'].search([
            ('activity_id', 'in', activity.ids),
        ])
        traces_info = []
        for trace in traces:
            record = all_records.filtered(lambda r: r.id == trace.res_id)
            record_info = ""
            if record:
                record_info = f"ID.{record.id}, {record.display_name}: email {record.email_normalized}"
                if "mobile" in record:
                    record_info += f"- mobile {record.mobile}"
                if "phone" in record:
                    record_info += f"- phone {record.phone}"
            traces_info.append(
                f'Trace: doc {trace.res_id} - activity {trace.activity_id.id} ({trace.activity_id.activity_type}) - status {trace.state}'
                f' - rec: {record_info})'
            )
        debug_info = '\n'.join(traces_info)

        # check traces / records coherency through campaign
        canceled_res_ids = canceled_res_ids or set()
        all_record_ids = set(all_records.ids) | canceled_res_ids
        if strict:
            self.assertEqual(
                set(traces.mapped('res_id')), all_record_ids,
                f'Should find one trace / record. Found\n{debug_info}'
            )
            self.assertEqual(
                len(traces), len(all_records) + len(canceled_res_ids),
                f'Should find one trace / record. Found\n{debug_info}'
            )
        else:
            self.assertTrue(set(all_record_ids) < set(traces.mapped('res_id')))
        for canceled_res_id in canceled_res_ids:
            linked_trace = traces.filtered(lambda t: t.res_id == canceled_res_id)
            self.assertTrue(linked_trace)
            self.assertEqual(linked_trace.state, 'canceled')

        if trace_values:
            _logger.warning('Not supported anymore, please update tests')
        for key, value in (trace_values or {}).items():
            self.assertEqual(set(traces.mapped(key)), set([value]))

        for info in participants_info:
            # check input
            invalid = set(info.keys()) - {
                'fields_values',
                'participants',
                'records', 'records_to_trace_email',
                'records_to_email_to_mail', 'records_to_email_to_recipients',
                'records_to_partner', 'records_to_trace_status',
                'status',  # marketing.trace status
                'trace_content', 'trace_email',
                'trace_email_to_mail', 'trace_email_to_recipients',
                'trace_failure_reason', 'trace_failure_type',
                'trace_status',  # mailing.trace status
                'mail_values',
                # sms (see sms modules)
                'check_sms',
                'trace_sms_number',
                # whatsapp (see wa modules)
                'wa_from_mock',
            }
            if invalid:
                raise AssertionError(f"assertMarketAutoTraces: invalid input {invalid}")

            records = info['records']
            linked_traces = traces.filtered(lambda t: t.res_id in records.ids)

            # check link to records, continue if no records (aka no traces)
            if not records:
                self.assertFalse(linked_traces)
                continue
            self.assertEqual(set(linked_traces.mapped('res_id')), set(info['records'].ids))

            # check trace details
            fields_values = info.get('fields_values') or {}
            for trace in linked_traces:
                record = records.filtered(lambda r: r.id == trace.res_id)
                trace_info = f'Trace {trace.id}: doc {trace.res_id} ({record.email_normalized}-{record.name})'

                # asked marketing.trace values
                self.assertEqual(
                    trace.state, info['status'],
                    f"Received {trace.state} instead of {info['status']} for {trace_info}\nDebug\n{debug_info}")
                for fname, fvalue in fields_values.items():
                    with self.subTest(fname=fname, fvalue=fvalue):
                        if fname == 'state_msg_content':
                            self.assertIn(
                                fvalue, trace['state_msg'],
                                f"Marketing Trace: expected {fvalue} for {fname}, not found in {trace['state_msg']} for {trace_info}"
                            )
                        else:
                            self.assertEqual(
                                trace[fname], fvalue,
                                f'Marketing Trace: expected {fvalue} for {fname}, got {trace[fname]} for {trace_info}'
                            )

            # check sub-records (mailing related notably)
            if info.get('trace_status') and activity.activity_type == 'mail':
                self.assertMarketAutoTracesMail(info, activity, traces)
            elif not info.get('trace_status'):
                self.assertEqual(linked_traces.mailing_trace_ids, self.env['mailing.trace'])

            if info.get('participants'):
                self.assertEqual(traces.participant_id, info['participants'])
        return traces

    def assertMarketAutoTracesMail(self, participant_info, activity, traces):
        # prepare optional record-specific values
        partners = participant_info.get('records_to_partner', {})
        trace_emails = participant_info.get('records_to_trace_email', {})
        mail_emails = participant_info.get('records_to_email_to_mail', {})
        email_emails = participant_info.get('records_to_email_to_recipients', {})
        statuses = participant_info.get('records_to_trace_status', {})
        records_add_info = []
        for record in participant_info['records']:
            add_info = {
                'email': trace_emails.get(record.id, participant_info.get('trace_email', record.email_normalized)),
                'partner': partners.get(record.id) or self.env['res.partner'],
                'trace_status': statuses.get(record.id) or participant_info['trace_status'],
            }

            if record.id in mail_emails:
                add_info['email_to_mail'] = mail_emails[record.id]
            elif 'trace_email_to_mail' in participant_info:
                add_info['email_to_mail'] = participant_info['trace_email_to_mail']
            elif not partners.get(record.id):
                add_info['email_to_mail'] = record.email_normalized or record[record._primary_email]

            if record.id in email_emails:
                add_info['email_to_recipients'] = email_emails[record.id]
            elif 'trace_email_to_recipients' in participant_info:
                add_info['email_to_recipients'] = participant_info['trace_email_to_recipients']
            records_add_info.append(add_info)
        self.assertMailTraces(
            [{
                # record info
                'record': record,
                # mail.mail
                'content': participant_info.get('trace_content'),
                'failure_type': participant_info.get('trace_failure_type', False),
                'failure_reason': participant_info.get('trace_failure_reason', False),
                'mail_values': participant_info.get('mail_values'),
                # mailing.trace + mail info
                **add_info,
                } for record, add_info in zip(participant_info['records'], records_add_info)
            ],
            activity.mass_mailing_id,
            participant_info['records'],
        )

    def assertActivityWoTrace(self, activities):
        """ Ensure activity has no traces linked to it """
        for activity in activities:
            with self.subTest(activity=activity):
                self.assertMarketAutoTraces([{'records': self.env[activity.model_name]}], activity)

    # ------------------------------------------------------------
    # RECORDS TOOLS
    # ------------------------------------------------------------

    @classmethod
    def _create_mailing(cls, model, user=None, **mailing_values):
        mailing_type = mailing_values.get("mailing_type", "mail")
        vals = {
            'body_html': """<div><p>Hello {{ object.name }}<br/>You rock</p>
<p>click here <a id="url0" href="https://www.example.com/foo/bar?baz=qux">LINK</a></p>
</div>""",
            'mailing_model_id': cls.env['ir.model']._get_id(model),
            'mailing_type': mailing_type,
            'name': 'SourceName',
            'preview': 'Hi {{ object.name }} :)',
            'reply_to_mode': 'update',
            'subject': 'Test for {{ object.name }}',
            'use_in_marketing_automation': True,
        }
        if mailing_type == 'mail':
            vals['body_html'] = """<div><p>Hello {{ object.name }}<br/>You rock</p>
<p>click here <a id="url0" href="https://www.example.com/foo/bar?baz=qux">LINK</a></p>
</div>"""
        else:
            vals['body_plaintext'] = "Test SMS for {{ object.name }} click on https://www.example.com/foo/bar?baz=qux"

        if user:
            vals['email_from'] = user.email_formatted
            vals['user_id'] = user.id
        vals.update(**mailing_values)
        return cls.env['mailing.mailing'].create(vals)

    @classmethod
    def _create_server_action(cls, model, code, **sa_values):
        vals = {
            "code": code,
            "model_id": cls.env["ir.model"]._get_id(model),
            "name": "Test SA",
            "state": "code",
        }
        vals.update(**sa_values)
        return cls.env['ir.actions.server'].create(vals)

    @classmethod
    def _create_activity(cls, campaign, mailing=None, wa_template=None, action=None, **act_values):
        vals = {}
        if mailing:
            if mailing.mailing_type == 'mail':
                vals.update({
                    'mass_mailing_id': mailing.id,
                    'activity_type': 'email',
                })
            else:
                vals.update({
                    'mass_mailing_id': mailing.id,
                    'activity_type': 'sms',
                })
        elif wa_template:
            vals.update({
                'activity_type': 'whatsapp',
                'whatsapp_template_id': wa_template.id,
            })
        elif action:
            vals.update({
                'server_action_id': action.id,
                'activity_type': 'action',
            })
        vals.update({
            'name': f'Activity {len(campaign.marketing_activity_ids) + 1} ({vals["activity_type"]} on {act_values.get("trigger_type")})',
            'campaign_id': campaign.id,
        })
        vals.update(**act_values)
        if act_values.get('create_date'):
            with patch.object(cls.env.cr, 'now', lambda: act_values['create_date']):
                activity = cls.env['marketing.activity'].create(vals)
        else:
            activity = cls.env['marketing.activity'].create(vals)
        return activity

    @classmethod
    def _create_activity_mail(cls, campaign, user=None, mailing_values=None, act_values=None):
        new_mailing = cls._create_mailing(campaign.model_name, user=user, **(mailing_values or {}))
        return cls._create_activity(campaign, mailing=new_mailing, **(act_values or {}))

    @classmethod
    def _create_activity_sa(cls, campaign, code, sa_values=None, act_values=None):
        new_sa = cls._create_server_action(campaign.model_name, code, **(sa_values or {}))
        return cls._create_activity(campaign, action=new_sa, **(act_values or {}))

    @classmethod
    def _create_activity_wa(cls, campaign, user=None, template_values=None, act_values=None):
        new_wa_template = cls._create_wa_template(campaign.model_name, user=user, **(template_values or {}))
        return cls._create_activity(campaign, wa_template=new_wa_template, **(act_values or {}))

    def _force_activity_create_date(self, activities, create_date):
        """ As create_date is set through sql NOW it is not possible to mock
        it easily. """
        self.env.cr.execute(
            "UPDATE marketing_activity SET create_date=%s WHERE id IN %s",
            (create_date, tuple(activities.ids),)
        )

    def _launch_campaign(self, campaign, date_reference=None):
        with self.mock_datetime_and_now(date_reference or fields.Datetime.now()):
            campaign.action_start_campaign()
            campaign.sync_participants()


class MarketingAutomationCommon(MarketingAutomationCase, MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_marketing_automation = mail_new_test_user(
            cls.env,
            email='user.marketing.automation@test.example.com',
            groups='base.group_user,base.group_partner_manager,marketing_automation.group_marketing_automation_user',
            login='user_marketing_automation',
            name='Mounhir MarketAutoUser',
            signature='--\nM'
        )

        countries = [cls.env.ref('base.be'), cls.env.ref('base.in')]
        cls.test_contacts = cls.env['mailing.contact'].create([
            {
                'country_id': countries[idx % len(countries)].id,
                'email': f'ma.test.contact.{idx}@example.com',
                'name': f'MATest_{idx}',
            }
            for idx in range(10)
        ])
        cls.campaign = cls.env['marketing.campaign'].create({
            'domain': [('name', 'like', 'MATest')],
            'model_id': cls.env['ir.model']._get_id('mailing.contact'),
            'name': 'Test Campaign',
        })
