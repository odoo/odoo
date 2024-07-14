# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mass_mailing.tests.common import MassMailCase, MassMailCommon


class MarketingAutomationCase(MassMailCase):

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

    def assertMarketAutoTraces(self, participants_info, activity, **trace_values):
        """ Check content of traces.

        :param participants_info: [{
            # participants
            'participants': participants record_set,      # optional: allow to check coherency of expected participants
            'records': records,                           # records going through this activity
            'status': status,                             # marketing trace status (processed, ...) for all records
            # marketing trace
            'fields_values': dict                         # optional fields values to check on marketing.trace
            'schedule_date': datetime or False,           # optional: check schedule_date on marketing trace
            # mailing/sms trace
            'trace_author': author of mail/sms            # used notably to ease finding emails / sms
            'trace_content': content of mail/sms          # content of sent mail / sms
            'trace_email': email logged on trace          # may differ from 'email_normalized'
            'trace_failure_type': failure_type of trace   # to check status update in case of failure
            'trace_status': status of mailing trace,      # if not set: check there is no mailing trace
        }, {}, ... ]
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
            if record:
                traces_info.append(
                    f'Trace: doc {trace.res_id} - activity {trace.activity_id.id} - status {trace.state} (rec {record.email_normalized}-{record.id})'
                )
            else:
                traces_info.append(
                    f'Trace: doc {trace.res_id} - activity {trace.activity_id.id} - status {trace.state}'
                )
        debug_info = '\n'.join(traces_info)
        self.assertEqual(
            set(traces.mapped('res_id')), set(all_records.ids),
            f'Should find one trace / record. Found\n{debug_info}'
        )
        self.assertEqual(
            len(traces), len(all_records),
            f'Should find one trace / record. Found\n{debug_info}'
        )

        for key, value in (trace_values or {}).items():
            self.assertEqual(set(traces.mapped(key)), set([value]))

        for info in participants_info:
            records = info['records']
            linked_traces = traces.filtered(lambda t: t.res_id in records.ids)

            # check link to records, continue if no records (aka no traces)
            if not records:
                self.assertFalse(linked_traces)
                continue
            self.assertEqual(set(linked_traces.mapped('res_id')), set(info['records'].ids))

            # check trace details
            fields_values = info.get('fields_values') or {}
            if 'schedule_date' in info:
                fields_values['schedule_date'] = info.get('schedule_date')
            for trace in linked_traces:
                record = records.filtered(lambda r: r.id == trace.res_id)
                trace_info = f'Trace: doc {trace.res_id} ({record.email_normalized}-{record.name})'

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
            if info.get('trace_status'):
                if activity.mass_mailing_id.mailing_type == 'mail':
                    self.assertMailTraces(
                        [{
                            # mailing.trace
                            'partner': self.env['res.partner'],  # TDE FIXME: make it generic and check why partner seems unset
                            'email': info.get('trace_email', record.email_normalized),
                            'record': record,
                            'state': info['trace_status'],
                            'trace_status': info['trace_status'],
                            # mail.mail
                            'content': info.get('trace_content'),
                            'failure_type': info.get('trace_failure_type', False),
                            'failure_reason': info.get('trace_failure_reason', False),
                            'mail_values': info.get('mail_values'),
                         } for record in info['records']
                        ],
                        activity.mass_mailing_id,
                        info['records'],
                    )
            else:
                self.assertEqual(linked_traces.mailing_trace_ids, self.env['mailing.trace'])

            if info.get('participants'):
                self.assertEqual(traces.participant_id, info['participants'])

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
        vals = {
            'body_html': """<div><p>Hello {{ object.name }}<br/>You rock</p>
<p>click here <a id="url0" href="https://www.example.com/foo/bar?baz=qux">LINK</a></p>
</div>""",
            'mailing_model_id': cls.env['ir.model']._get_id(model),
            'mailing_type': 'mail',
            'name': 'SourceName',
            'preview': 'Hi {{ object.name }} :)',
            'reply_to_mode': 'update',
            'subject': 'Test for {{ object.name }}',
            'use_in_marketing_automation': True,
        }
        if user:
            vals['email_from'] = user.email_formatted
            vals['user_id'] = user.id
        vals.update(**mailing_values)
        return cls.env['mailing.mailing'].create(vals)

    @classmethod
    def _create_activity(cls, campaign, mailing=None, action=None, **act_values):
        vals = {
            'name': f'Activity {len(campaign.marketing_activity_ids) + 1}',
            'campaign_id': campaign.id,
        }
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
        elif action:
            vals.update({
                'server_action_id': action.id,
                'activity_type': 'action',
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

    def _force_activity_create_date(self, activities, create_date):
        """ As create_date is set through sql NOW it is not possible to mock
        it easily. """
        self.env.cr.execute(
            "UPDATE marketing_activity SET create_date=%s WHERE id IN %s",
            (create_date, tuple(activities.ids),)
        )


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
