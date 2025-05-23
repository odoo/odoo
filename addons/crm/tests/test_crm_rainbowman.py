from datetime import datetime

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import tagged, users


@tagged('lead_internals')
class TestCrmLeadRainbowmanMessages(TestCrmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # unlink all leads from sales_team_1
        cls.env['crm.lead'].search([
            ('team_id', '=', cls.sales_team_1.id),
        ]).unlink()

        cls.company_casey = cls.env['res.company'].create({
            'name': 'company_casey',
        })
        cls.sales_manager_casey = mail_new_test_user(
            cls.env,
            login='sales_manager_casey',
            name='sales_manager_casey',
            groups='sales_team.group_sale_manager,base.group_partner_manager',
            company_id=cls.company_casey.id,
            company_ids=[(4, cls.company_casey.id)],
        )

        # cls.env['crm.team.member'].create([
        #     {'user_id': cls.user_sales_manager.id, 'crm_team_id': cls.sales_team_1.id},
        #     {'user_id': cls.user_sales_salesman.id, 'crm_team_id': cls.sales_team_1.id},
        # ])

    def _update_create_date(self, lead, date):
        self.env.cr.execute("""
            UPDATE crm_lead
            SET create_date = %(date)s
            WHERE id = %(lead_id)s
        """, {
            'lead_id': lead.id,
            'date': date,
        })
        lead.invalidate_recordset(['create_date'])

    def _set_won_get_rainbowman_message(self, lead, user, reset_team=False):
        """
        Assign the passed user and set the lead as won.
        Then, if there's a message, return that message.
        Otherwise, as the result for action_set_won_rainbowman() if there's no message is True,
        return False to make testing code more readable.
        """

        # lead.user_id = user
        # # If reset_team is passed, reset the team to False, as otherwise assigning a user will automatically assign a team
        # if reset_team:
        #     lead.team_id = False
        lead.update({
            'user_id': user.id,
            'team_id': False if reset_team else lead.team_id.id,
        })

        rainbowman_action_result = lead.with_user(user).action_set_won_rainbowman()
        if rainbowman_action_result and not isinstance(rainbowman_action_result, bool):
            return rainbowman_action_result['effect']['message']
        return False

    @users('user_sales_manager')
    def test_leads_rainbowman(self):
        """
        This test ensures that all rainbowman messages can trigger, and that they do so in correct order of priority.
        """

        # setup timestamps:
        past = datetime(2024, 12, 15, 12, 0)
        jan1_10am = datetime(2025, 1, 1, 10, 0)
        jan1_12pm = datetime(2025, 1, 1, 12, 0)
        jan2 = datetime(2025, 1, 2, 12, 0)
        jan3_12pm = datetime(2025, 1, 3, 12, 0)
        jan3_1pm = datetime(2025, 1, 3, 13, 0)
        jan4 = datetime(2025, 1, 4, 12, 0)
        jan12 = datetime(2025, 1, 12, 12, 0)
        march1 = datetime(2025, 3, 1, 12, 0)

        # setup main batch of leads
        with self.mock_datetime_and_now(past):
            leads_norevenue = self._create_leads_batch(
                count=15,
                partner_count=5,
                user_ids=[self.user_sales_manager.id, self.user_sales_salesman.id],
                lead_type='opportunity',
                additional_lead_values={
                    'stage_id': self.stage_team1_1.id,
                },
            )
            leads_revenue = self._create_leads_batch(
                count=18,
                partner_count=3,
                user_ids=[self.user_sales_manager.id, self.user_sales_salesman.id],
                lead_type='opportunity',
                additional_lead_values={
                    'expected_revenue': 500,
                    'stage_id': self.stage_team1_1.id,
                },
            )
            iter_leads_norevenue = iter(leads_norevenue)
            iter_leads_revenue = iter(leads_revenue)
            all_leads = leads_norevenue | leads_revenue
            # initialize tracking
            self.flush_tracking()

        # test lead rainbowman messages (leads without expected revenues)

        with self.mock_datetime_and_now(jan1_10am):
            self.flush_tracking()
            all_leads.invalidate_recordset(['duration_tracking'])

            # switch the stage to avoid having the "first to last stage" message show up all the time
            all_leads.write({'stage_id': self.stage_team1_2.id})
            # flush tracking to make sure it's taken into account
            self.flush_tracking()
            all_leads.invalidate_recordset(['duration_tracking'])

            msg_firstdeal = self._set_won_get_rainbowman_message(next(iter_leads_norevenue), self.user_sales_manager)
            self.assertEqual(
                msg_firstdeal,
                'Go, go, go! Congrats for your first deal.',
                'First deal',
            )

            lead_25messages = next(iter_leads_norevenue)
            self.env['mail.message'].create([
                {
                    'model': 'crm.lead',
                    'res_id': lead_25messages.id,
                    'body': 'Message',
                    'message_type': 'comment',
                } for x in range(25)
            ])
            msg_25messages = self._set_won_get_rainbowman_message(lead_25messages, self.user_sales_manager)
            self.assertEqual(
                msg_25messages,
                'Phew, that took some effort — but you nailed it. Good job!',
                'Win with 25 messages on the counter',
            )

        with self.mock_datetime_and_now(jan1_12pm):
            self.flush_tracking()
            all_leads.invalidate_recordset(['duration_tracking'])

            lead_other_first_with_revenue = next(iter_leads_norevenue)
            lead_other_first_with_revenue.expected_revenue = 100
            msg_other_first_with_revenue = self._set_won_get_rainbowman_message(lead_other_first_with_revenue, self.user_sales_salesman)
            self.assertEqual(
                msg_other_first_with_revenue,
                'Go, go, go! Congrats for your first deal.',
                'First deal (another user), even with record revenue',
            )

            lead_first_country = next(iter_leads_norevenue)
            lead_first_country.country_id = self.env.ref('base.au')
            msg_first_country = self._set_won_get_rainbowman_message(lead_first_country, self.user_sales_manager)
            self.assertEqual(
                msg_first_country,
                'You just expanded the map! First win in Australia.',
                'First win in a country (all team)',
            )

            lead_second_country = next(iter_leads_norevenue)
            lead_second_country.country_id = self.env.ref('base.au')
            msg_second_country = self._set_won_get_rainbowman_message(lead_second_country, self.user_sales_salesman)
            self.assertFalse(
                msg_second_country,
                'Second deal from the same country (all team)',
            )

            source_facebook_ad = self.env['utm.source'].create({'name': 'Facebook Ad'})
            lead_first_source = next(iter_leads_norevenue)
            lead_first_source.source_id = source_facebook_ad
            msg_first_source = self._set_won_get_rainbowman_message(lead_first_source, self.user_sales_manager)
            self.assertEqual(
                msg_first_source,
                'Yay, your first win from Facebook Ad!',
                'First win from a UTM source (all team)',
            )

            lead_second_source = next(iter_leads_norevenue)
            lead_second_source.source_id = source_facebook_ad.id
            msg_second_source = self._set_won_get_rainbowman_message(lead_second_source, self.user_sales_salesman)
            self.assertFalse(
                msg_second_source,
                'Second deal from the same source (all team)',
            )

            lead_combo5 = next(iter_leads_norevenue)
            msg_combo5 = self._set_won_get_rainbowman_message(lead_combo5, self.user_sales_manager)
            self.assertEqual(
                msg_combo5,
                'You\'re on fire! Fifth deal won today 🔥',
                'Fifth deal won today (user)',
            )

        with self.mock_datetime_and_now(jan2):
            self.flush_tracking()
            all_leads.invalidate_recordset(['duration_tracking'])

            # fast closes:
            # 10 days ago
            lead_fastclose_10 = next(iter_leads_norevenue)
            self._update_create_date(lead_fastclose_10, datetime(2024, 12, 22))
            msg_fastclose_10 = self._set_won_get_rainbowman_message(lead_fastclose_10, self.user_sales_manager)
            self.assertEqual(
                msg_fastclose_10,
                'Wow, that was fast. That deal didn’t stand a chance!',
                'Fastest close in 30 days',
            )

            # 15 days ago
            lead_fastclose_15 = next(iter_leads_norevenue)
            self._update_create_date(lead_fastclose_15, datetime(2024, 12, 17))
            msg_fastclose_15 = self._set_won_get_rainbowman_message(lead_fastclose_15, self.user_sales_manager)
            self.assertFalse(
                msg_fastclose_15,
                'Not the fastest close in 30 days',
            )

            # Today
            lead_fastclose_0 = next(iter_leads_norevenue)
            self._update_create_date(lead_fastclose_0, jan1_12pm)
            msg_fastclose_0 = self._set_won_get_rainbowman_message(lead_fastclose_0, self.user_sales_manager)
            self.assertEqual(
                msg_fastclose_0,
                'Wow, that was fast. That deal didn’t stand a chance!',
                'Fastest close in 30 days',
            )

            self.assertFalse(
                self._set_won_get_rainbowman_message(next(iter_leads_norevenue), self.user_sales_salesman),
                'No achievment reached',
            )

        with self.mock_datetime_and_now(jan3_12pm):
            self.flush_tracking()
            all_leads.invalidate_recordset(['duration_tracking'])

            lead_3daystreak = next(iter_leads_norevenue)
            msg_3daystreak = self._set_won_get_rainbowman_message(lead_3daystreak, self.user_sales_manager)
            self.assertEqual(
                msg_3daystreak,
                'You\'re on a winning streak. 3 deals in 3 days, congrats!',
                'Three-day streak',
            )

        with self.mock_datetime_and_now(jan3_1pm):
            self.flush_tracking()
            all_leads.invalidate_recordset(['duration_tracking'])

            # Create new lead with no changed stage to get 'straight to the win' message

            lead_first_to_last = self.env['crm.lead'].create({
                'name': 'lead',
                'type': 'opportunity',
                'stage_id': self.stage_team1_1.id,
                'user_id': self.user_sales_manager.id,
            })
            self._update_create_date(lead_first_to_last, jan1_12pm)
            self.flush_tracking()
            all_leads.invalidate_recordset(['duration_tracking'])
            msg_first_to_last = self._set_won_get_rainbowman_message(lead_first_to_last, self.user_sales_manager)
            self.assertEqual(
                msg_first_to_last,
                'No detours, no delays - from New straight to the win! 🚀',
                'First stage to last stage',
            )

            self.assertFalse(
                self._set_won_get_rainbowman_message(next(iter_leads_norevenue), self.user_sales_manager),
                'Check that no message is returned if no "achievement" is reached',
            )

        with self.mock_datetime_and_now(jan4):
            # test lead rainbowman messages (leads with expected revenues)
            last_30_days_cases = [
                (self.user_sales_manager, 650, 'Boom! Team record for the past 30 days.'),
                (self.user_sales_manager, 550, False),
                (self.user_sales_manager, 700, 'Boom! Team record for the past 30 days.'),
                (self.user_sales_manager, 700, False),
                (self.user_sales_salesman, 600, 'You just beat your personal record for the past 30 days.'),
                (self.user_sales_salesman, 600, False),
                (self.user_sales_salesman, 550, False),
                (self.user_sales_salesman, 1000, 'Boom! Team record for the past 30 days.'),
                (self.user_sales_manager, 950, 'You just beat your personal record for the past 30 days.'),
            ]
            for user, expected_revenue, expected_message in last_30_days_cases:
                with self.subTest(user=user, revenue=expected_revenue):
                    lead_revenue = next(iter_leads_revenue)
                    lead_revenue.expected_revenue = expected_revenue
                    msg_revenue = self._set_won_get_rainbowman_message(lead_revenue, user)
                    self.assertEqual(msg_revenue, expected_message)

        with self.mock_datetime_and_now(jan12):
            last_7_days_cases = [
                (self.user_sales_manager, 650, 'Yeah! Best deal out of the last 7 days for the team.'),
                (self.user_sales_manager, 500, False),
                (self.user_sales_manager, 650, False),
                (self.user_sales_manager, 800, 'Yeah! Best deal out of the last 7 days for the team.'),
                (self.user_sales_salesman, 700, 'You just beat your personal record for the past 7 days.'),
                (self.user_sales_salesman, 650, False),
                (self.user_sales_salesman, 750, 'You just beat your personal record for the past 7 days.'),
                (self.user_sales_salesman, 850, 'Yeah! Best deal out of the last 7 days for the team.'),
            ]
            for user, expected_revenue, expected_message in last_7_days_cases:
                with self.subTest(user=user, revenue=expected_revenue):
                    lead_revenue = next(iter_leads_revenue)
                    lead_revenue.expected_revenue = expected_revenue
                    msg_revenue = self._set_won_get_rainbowman_message(lead_revenue, user)
                    self.assertEqual(msg_revenue, expected_message)

        with self.mock_datetime_and_now(march1):
            lead_later_record = next(iter_leads_revenue)
            lead_later_record.expected_revenue = 750
            msg_later_record = self._set_won_get_rainbowman_message(lead_later_record, self.user_sales_manager)
            self.assertEqual(msg_later_record, 'Boom! Team record for the past 30 days.', 'Once a month has passed, \
                monthly team records may be set even if the amount was lower than the alltime max.')

    @users('user_sales_manager')
    def test_leads_rainbowman_timezones(self):
        """
        Users in differing timezones need to get appropriate time-based messages.
        This test verifies that users in distant timezones still get rainbowman messages
        when it makes sense from their own point of view.
        """
        sales_m10 = mail_new_test_user(         # UTC-10
            self.env(su=True),
            login='polynesia_-10',
            tz='Pacific/Honolulu',
            name='polynesia_-10',
            groups='sales_team.group_sale_manager',
        )
        sales_p530 = mail_new_test_user(        # UTC+5:30
            self.env(su=True),
            login='india_+5:30',
            tz='Asia/Kolkata',
            name='india_+5:30',
            groups='sales_team.group_sale_manager',
        )
        sales_p13 = mail_new_test_user(         # UTC+13
            self.env(su=True),
            login='samoa_+13',
            tz='Pacific/Apia',
            name='samoa_+13',
            groups='sales_team.group_sale_manager',
        )
        sales_users = [sales_m10, sales_p530, sales_p13]

        # All datetimes stored in-DB are in UTC
        jan9_10_45am = datetime(2025, 1, 9, 10, 45, 0)  # first deal
        jan9_11_30am = datetime(2025, 1, 9, 11, 30, 0)
        jan9_4pm = datetime(2025, 1, 9, 16, 0)
        jan9_6_45pm = datetime(2025, 1, 9, 18, 45)
        jan9_11pm = datetime(2025, 1, 9, 23, 0)         # polynesia_m10: fifth deal in a day
        jan10_midnight = datetime(2025, 1, 10, 0, 0)    # samoa_p13: fifth deal in a day
        jan10_3am = datetime(2025, 1, 10, 3, 0)
        jan10_8am = datetime(2025, 1, 10, 8, 0)         # india_p530: fifth deal in a day
        jan10_11am = datetime(2025, 1, 10, 11, 0)       # samoa_p13: three-day streak

        first_deal = 'Go, go, go! Congrats for your first deal.'
        fifth_deal_day = 'You\'re on fire! Fifth deal won today 🔥'
        three_day_streak = 'You\'re on a winning streak. 3 deals in 3 days, congrats!'
        cases = [
            (jan9_10_45am, {user: first_deal for user in sales_users}),
            (jan9_11_30am, {}),
            (jan9_4pm, {}),
            (jan9_6_45pm, {}),
            (jan9_11pm, {sales_m10: fifth_deal_day}),
            (jan10_midnight, {sales_p13: fifth_deal_day}),
            (jan10_3am, {}),
            (jan10_8am, {sales_p530: fifth_deal_day}),
            (jan10_11am, {sales_p13: three_day_streak}),
        ]
        leads = self._create_leads_batch(
            count=27,
            lead_type='opportunity',
            additional_lead_values={
                'stage_id': self.stage_team1_1.id,
            },
        )
        iter_leads = iter(leads)
        for deal_closing_time, expected_messages in cases:
            with self.mock_datetime_and_now(deal_closing_time):
                for sales_user in sales_users:
                    with self.subTest(username=sales_user.name, time=deal_closing_time):
                        msg = self._set_won_get_rainbowman_message(next(iter_leads), sales_user)
                        self.assertEqual(msg, expected_messages.get(sales_user, False))

    @users('sales_manager_casey')
    def test_leads_rainbowman_no_team(self):
        past = datetime(2025, 1, 2, 12, 0)
        past_1pm = datetime(2025, 1, 2, 13, 0)
        now = datetime(2025, 1, 5, 12, 0)

        with self.mock_datetime_and_now(past):
            leads = self._create_leads_batch(
                count=6,
                user_ids=[self.sales_manager_casey.id, self.user_sales_salesman.id],
                lead_type='opportunity',
                additional_lead_values={
                    'stage_id': self.stage_team1_1.id,
                },
            )
            iter_leads = iter(leads)

        with self.mock_datetime_and_now(past_1pm):
            # prime the users and leads (to skip first deal closed, fastest close, from first to last...)
            self.flush_tracking()
            leads.stage_id = self.stage_gen_1
            self.flush_tracking()
            lead_prime_casey = next(iter_leads)
            lead_prime_benoit = next(iter_leads)
            self._set_won_get_rainbowman_message(lead_prime_casey, self.sales_manager_casey, reset_team=True)
            self._set_won_get_rainbowman_message(lead_prime_benoit, self.user_sales_salesman)

        with self.mock_datetime_and_now(now):
            source_xitter_post = self.env['utm.source'].create({'name': 'Xitter Post'})
            lead_noteam = next(iter_leads)
            lead_noteam.source_id = source_xitter_post
            msg_lead_noteam = self._set_won_get_rainbowman_message(lead_noteam, self.sales_manager_casey, reset_team=True)
            self.assertEqual(
                msg_lead_noteam,
                'Yay, your first win from Xitter Post!',
                'First win from a UTM source (lead has no team)',
            )

            # (complete an empty lead to skip the fifth row in a day message)
            self._set_won_get_rainbowman_message(next(iter_leads), self.sales_manager_casey)

            lead_noteam_samesource = next(iter_leads)
            lead_noteam_samesource.source_id = source_xitter_post
            msg_lead_noteam_samesource = self._set_won_get_rainbowman_message(lead_noteam_samesource, self.sales_manager_casey, reset_team=True)
            self.assertFalse(
                msg_lead_noteam_samesource,
                'Second deal from the same source (no team) triggers no message if the source has already been won once for the user',
            )

            lead_inteam_samesource = next(iter_leads)
            lead_inteam_samesource.source_id = source_xitter_post
            msg_lead_inteam_samesource = self._set_won_get_rainbowman_message(lead_inteam_samesource, self.user_sales_salesman)
            self.assertEqual(
                msg_lead_inteam_samesource,
                'Yay, your first win from Xitter Post!',
                'Benoit can still receive the message as neither he nor his team have a recorded win for this source',
            )
