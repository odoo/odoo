# -*- coding: utf-8 -*-
"""Tests for the Postlog Data (Postlog) workbench.

Mirrors tests/test_prelog_fuzzy_matching.py case-for-case where the behaviour is
shared, and adds the cases that only exist on the postlog side:

  * ``length`` is a Selection (``v_30``) rather than a Char ("30").
  * post-midnight (vendor "XM") air times against overnight rotations.
  * re-importing a week is blocked rather than replacing it.
  * there is no ``version`` and no ``removed``.

Program naming matters here. ``load_program_config`` slugifies the program name,
so a program called "True Crime Network" picks up postlog_configs/
true_crime_network.json - which sets ``useProgramForNetwork`` and declares
neither ``networkNames`` nor ``fieldMap['network']``, so network checking is
bypassed. Any other name falls back to default.json, which does declare
``fieldMap['network']`` and therefore enforces the network match. Both paths are
covered below.
"""
import csv
import io
from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestPostlogMatching(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.week = date(2026, 7, 27)          # a Monday
        cls.Postlog = cls.env['mv.spot_data']

        # Falls back to postlog_configs/default.json -> network check ACTIVE.
        cls.program = cls.env['mv.programs'].create({
            'name': 'Postlog Test Network',
            'clientcode': 'SPT',
            'clock_start_time': 'v_6am',
        })
        cls.other_program = cls.env['mv.programs'].create({
            'name': 'Other Postlog Network',
            'clientcode': 'OSP',
            'clock_start_time': 'v_6am',
        })

        cls.monday = cls.env['mv.days_allowed.tag'].search(
            [('name', '=ilike', 'Mon%')], limit=1,
        )
        if not cls.monday:
            cls.monday = cls.env['mv.days_allowed.tag'].create({'name': 'Mon'})
        cls.tuesday = cls.env['mv.days_allowed.tag'].search(
            [('name', '=ilike', 'Tue%')], limit=1,
        )
        if not cls.tuesday:
            cls.tuesday = cls.env['mv.days_allowed.tag'].create({'name': 'Tue'})

        cls.deal = cls.env['mv.deal'].create({
            'program': cls.program.id,
            'network_deal_number': 'SPT-100',
            'length': 'v_30',
        })
        cls.schedule = cls.env['mv.schedules'].create({
            'deal_parent': cls.deal.id,
            'week': cls.week,
            'start_time': 'v_09_00a',
            'end_time': 'v_10_00a',
            'days_allowed': [Command.set(cls.monday.ids)],
            'rate': 100.0,
            'status': 'sold',
        })

        # Same deal number under a different program - used to prove the
        # network/program guard actually rejects the wrong one.
        cls.other_deal = cls.env['mv.deal'].create({
            'program': cls.other_program.id,
            'network_deal_number': 'SPT-100',
            'length': 'v_30',
        })
        cls.other_schedule = cls.env['mv.schedules'].create({
            'deal_parent': cls.other_deal.id,
            'week': cls.week,
            'start_time': 'v_09_00a',
            'end_time': 'v_10_00a',
            'days_allowed': [Command.set(cls.monday.ids)],
            'rate': 100.0,
            'status': 'sold',
        })

    def _create_postlog(self, **overrides):
        values = {
            'import_program': self.program.id,
            'import_week_value': self.week,
            'broadcast_network': 'Postlog Test Network',
            'network_deal_number': 'SPT-100',
            'air_date': self.week,
            'air_time': '09:30:00',
            'length': 'v_30',
            'spot_rate': 100.0,
            'product': 'Test Advertiser / Product',
            'status': 'aired',
            'import_match_status': 'created_without_schedule',
        }
        values.update(overrides)
        return self.Postlog.create(values)

    def _search(self, **kwargs):
        return self.Postlog.fuzzy_match_search(
            self.program.id, self.week.isoformat(), **kwargs
        )

    # ------------------------------------------------------------------
    # Core happy path
    # ------------------------------------------------------------------

    def test_search_and_attach_suggested_schedule(self):
        postlog = self._create_postlog()

        result = self._search()
        self.assertEqual(result['total'], 1)
        row = result['rows'][0]
        self.assertEqual(row['id'], postlog.id)
        self.assertEqual(row['suggested']['id'], self.schedule.id)
        self.assertTrue(row['suggestion_attachable'])
        self.assertFalse(row['reason'])
        self.assertEqual(row['match_quality'], 'exact')

        applied = self.Postlog.fuzzy_match_apply([{
            'postlog_id': postlog.id,
            'schedule_id': self.schedule.id,
            'source': 'suggested',
        }], self.program.id, self.week.isoformat())
        self.assertEqual(applied['attached'], 1)
        self.assertEqual(postlog.schedule, self.schedule)
        self.assertEqual(postlog.import_match_status, 'matched')
        self.assertIn('Postlog Workbench', postlog.import_match_detail)

        # Re-attaching an already matched row must be refused.
        with self.assertRaises(UserError):
            self.Postlog.fuzzy_match_apply([{
                'postlog_id': postlog.id,
                'schedule_id': self.schedule.id,
                'source': 'suggested',
            }])

    def test_detach_returns_row_to_suggestion(self):
        postlog = self._create_postlog(schedule=self.schedule.id, import_match_status='matched')
        self.assertEqual(self._search()['counts']['matched'], 1)

        result = self.Postlog.fuzzy_match_detach(
            [postlog.id], self.program.id, self.week.isoformat()
        )
        self.assertEqual(result['updated'], 1)
        self.assertFalse(postlog.schedule)

        row = self._search()['rows'][0]
        self.assertEqual(row['status'], 'suggestion')
        self.assertEqual(row['suggested']['id'], self.schedule.id)

    # ------------------------------------------------------------------
    # Rejection paths
    # ------------------------------------------------------------------

    def test_out_of_rotation_is_a_fuzzy_suggestion_not_exact(self):
        self._create_postlog(air_time='13:00:00')
        row = self._search()['rows'][0]
        self.assertEqual(row['status'], 'suggestion')
        self.assertNotEqual(row['match_quality'], 'exact')
        self.assertTrue(row['reason'])

    def test_wrong_network_is_rejected_when_config_declares_one(self):
        self._create_postlog(broadcast_network='Some Other Network')
        row = self._search()['rows'][0]
        self.assertEqual(row['status'], 'no_suggestion')

    def test_program_config_may_bypass_the_network_check(self):
        """A TCN-style program trusts the selected program over the file value.

        postlog_configs/true_crime_network.json sets useProgramForNetwork and
        declares no networkNames, so _fuzzy_network_names returns False and any
        broadcast_network value is accepted. This pins that behaviour so a
        future config change cannot silently loosen or tighten matching.
        """
        tcn = self.env['mv.programs'].create({
            'name': 'True Crime Network',
            'clientcode': 'TCNT',
            'clock_start_time': 'v_6am',
        })
        deal = self.env['mv.deal'].create({
            'program': tcn.id, 'network_deal_number': 'TCNT-1', 'length': 'v_30',
        })
        schedule = self.env['mv.schedules'].create({
            'deal_parent': deal.id, 'week': self.week,
            'start_time': 'v_09_00a', 'end_time': 'v_10_00a',
            'days_allowed': [Command.set(self.monday.ids)],
            'rate': 100.0, 'status': 'sold',
        })
        self._create_postlog(
            import_program=tcn.id,
            network_deal_number='TCNT-1',
            broadcast_network='Totally Unrelated Network',
        )
        result = self.Postlog.fuzzy_match_search(tcn.id, self.week.isoformat())
        row = result['rows'][0]
        self.assertEqual(row['suggested']['id'], schedule.id)

    def test_rate_mismatch_is_a_fuzzy_suggestion(self):
        """A wrong rate is a real discrepancy, so show the schedule it nearly
        matched rather than a dead end."""
        self._create_postlog(spot_rate=999.0)
        row = self._search()['rows'][0]
        self.assertEqual(row['status'], 'suggestion')
        self.assertEqual(row['suggested']['id'], self.schedule.id)
        self.assertTrue(row['rate_mismatch'])
        self.assertNotEqual(row['match_quality'], 'exact')
        self.assertIn('rate', (row['reason'] or '').lower())

    def test_day_mismatch_is_a_fuzzy_suggestion(self):
        """Aired on a day the rotation does not run: still show the schedule."""
        self.schedule.days_allowed = [Command.set(self.monday.ids)]
        self._create_postlog(air_date=date(2026, 7, 28))      # a Tuesday
        row = self._search()['rows'][0]
        self.assertEqual(row['status'], 'suggestion')
        self.assertEqual(row['suggested']['id'], self.schedule.id)
        self.assertTrue(row['day_mismatch'])
        self.assertNotEqual(row['match_quality'], 'exact')
        self.assertIn('day', (row['reason'] or '').lower())

    def test_fixing_a_schedule_makes_it_exact_but_does_not_auto_attach(self):
        """Correcting a Schedule must show the row as ready, never attach it.

        Same contract as prelog: the row stays a Fuzzy Suggestion, the quality
        chip flips to exact and the reason clears, and a human still has to
        press Attach.
        """
        self.schedule.days_allowed = [Command.set(self.monday.ids)]
        postlog = self._create_postlog(air_date=date(2026, 7, 28))      # Tuesday
        row = self._search()['rows'][0]
        self.assertEqual(row['match_quality'], 'fuzzy')
        self.assertTrue(row['day_mismatch'])

        # the operator adds Tuesday to the rotation and re-runs
        self.schedule.days_allowed = [Command.link(self.tuesday.id)]
        row = self._search()['rows'][0]
        self.assertEqual(row['match_quality'], 'exact')           # chip says Exact
        self.assertFalse(row['reason'])                           # UI shows "Ready to attach"
        self.assertEqual(row['status'], 'suggestion')             # stays in Fuzzy Suggestions
        self.assertEqual(row['status_label'], 'Fuzzy Suggestion')
        self.assertTrue(row['suggestion_attachable'])
        self.assertFalse(postlog.schedule)                           # NOT auto-attached
        self.assertEqual(self._search()['counts']['matched'], 0)


    def test_mis_keyed_rate_does_not_push_the_postlog_to_another_rotation(self):
        """Regression for the 9:22pm case reported on the 8/24 prelogs.

        A postlog that aired inside the 9p-10p rotation must attach there and flag
        the bad rate, not jump to the 8p-9p rotation just because that one
        happens to carry the right rate. Where a postlog physically aired outranks
        an attribute somebody can mis-type.
        """
        early = self.env['mv.schedules'].create({           # postlog is 22 min outside
            'deal_parent': self.deal.id, 'week': self.week,
            'start_time': 'v_08_00p', 'end_time': 'v_09_00p',
            'days_allowed': [Command.set(self.monday.ids)],
            'rate': 100.0, 'status': 'sold',
        })
        correct = self.env['mv.schedules'].create({          # postlog aired in here
            'deal_parent': self.deal.id, 'week': self.week,
            'start_time': 'v_09_00p', 'end_time': 'v_10_00p',
            'days_allowed': [Command.set(self.monday.ids)],
            'rate': 555.0,                                   # mis-keyed
            'status': 'sold',
        })
        self._create_postlog(air_time='21:22:00', spot_rate=100.0)
        row = self._search()['rows'][0]

        self.assertEqual(row['suggested']['id'], correct.id)
        self.assertNotEqual(row['suggested']['id'], early.id)
        self.assertTrue(row['rate_mismatch'])
        self.assertIn('rate', (row['reason'] or '').lower())

        # and the 8p-9p schedule is still offered as an alternative
        alt_ids = [a['id'] for a in row['alternatives']]
        self.assertIn(early.id, alt_ids)

    def test_alternatives_are_ranked_and_explain_themselves(self):
        for start, end, rate in (('v_08_00p', 'v_09_00p', 100.0),
                                 ('v_10_00p', 'v_11_00p', 100.0)):
            self.env['mv.schedules'].create({
                'deal_parent': self.deal.id, 'week': self.week,
                'start_time': start, 'end_time': end,
                'days_allowed': [Command.set(self.monday.ids)],
                'rate': rate, 'status': 'sold',
            })
        self.env['mv.schedules'].create({
            'deal_parent': self.deal.id, 'week': self.week,
            'start_time': 'v_09_00p', 'end_time': 'v_10_00p',
            'days_allowed': [Command.set(self.monday.ids)],
            'rate': 100.0, 'status': 'sold',
        })
        self._create_postlog(air_time='21:22:00')
        row = self._search()['rows'][0]
        self.assertTrue(row['alternatives'])
        self.assertLessEqual(len(row['alternatives']), 4)
        for alt in row['alternatives']:
            self.assertIn('why', alt)
            self.assertIn('attachable', alt)
            self.assertNotEqual(alt['id'], row['suggested']['id'])

    def test_attaching_an_alternative_uses_the_manual_override_path(self):
        """The drawer's "Use this" sends schedule_id with source=manual."""
        other = self.env['mv.schedules'].create({
            'deal_parent': self.deal.id, 'week': self.week,
            'start_time': 'v_02_00p', 'end_time': 'v_03_00p',
            'days_allowed': [Command.set(self.monday.ids)],
            'rate': 100.0, 'status': 'sold',
        })
        postlog = self._create_postlog()
        result = self.Postlog.fuzzy_match_apply([{
            'postlog_id': postlog.id,
            'schedule_id': other.id,
            'source': 'manual',
            'confirmed_override': True,
        }], self.program.id, self.week.isoformat())
        self.assertEqual(result['attached'], 1)
        self.assertEqual(postlog.schedule, other)

    def test_ready_to_attach_issue_filter(self):
        """'Ready to attach' isolates exact-but-unattached rows for bulk attach."""
        ready = self._create_postlog()                              # exact
        self._create_postlog(spot_rate=999.0)                       # fuzzy, rate
        self._create_postlog(schedule=self.schedule.id, import_match_status='matched')
        rows = self._search(issue_filter='ready')['rows']
        self.assertEqual([r['id'] for r in rows], [ready.id])

    def test_missing_air_date_still_gives_no_suggestion(self):
        """A missing date is not a day *mismatch* - there is nothing to compare,
        so suggesting a schedule would be a guess."""
        self._create_postlog(air_date=False)
        row = self._search()['rows'][0]
        self.assertEqual(row['status'], 'no_suggestion')
        self.assertFalse(row['suggested'])
        self.assertIn('Missing air date', row['reason'])

    def test_right_day_and_rate_outrank_a_mismatching_sibling(self):
        """Ranking must prefer the candidate that matches day and rate."""
        wrong = self.env['mv.schedules'].create({
            'deal_parent': self.deal.id,
            'week': self.week,
            'start_time': 'v_09_00a',
            'end_time': 'v_10_00a',
            'days_allowed': [Command.set(self.tuesday.ids)],   # wrong day
            'rate': 555.0,                                     # wrong rate
            'status': 'sold',
        })
        self._create_postlog()
        row = self._search()['rows'][0]
        self.assertEqual(row['suggested']['id'], self.schedule.id)
        self.assertNotEqual(row['suggested']['id'], wrong.id)
        self.assertEqual(row['match_quality'], 'exact')

    def test_rate_and_day_issue_filters(self):
        rate_postlog = self._create_postlog(spot_rate=999.0)
        self.schedule.days_allowed = [Command.set(self.monday.ids)]
        day_postlog = self._create_postlog(air_date=date(2026, 7, 28))
        self.assertEqual(
            [r['id'] for r in self._search(issue_filter='rate')['rows']], [rate_postlog.id])
        self.assertEqual(
            [r['id'] for r in self._search(issue_filter='day')['rows']], [day_postlog.id])

    def test_network_mismatch_is_still_a_hard_stop(self):
        """Network stays the one hard boundary - a different network's schedule
        is the wrong record, not a near miss."""
        self._create_postlog(broadcast_network='Some Other Network')
        row = self._search()['rows'][0]
        self.assertEqual(row['status'], 'no_suggestion')
        self.assertFalse(row['suggested'])

    def test_wrong_day_is_not_silently_accepted(self):
        # Tuesday air date against a Monday-only rotation.
        self._create_postlog(air_date=date(2026, 7, 28))
        row = self._search()['rows'][0]
        self.assertNotEqual(row['match_quality'], 'exact')

    def test_canceled_schedule_is_found_but_not_attachable(self):
        self.schedule.status = 'canceled'
        self._create_postlog()
        row = self._search()['rows'][0]
        self.assertFalse(row['suggestion_attachable'])
        self.assertIn('cancel', (row['reason'] or '').lower())

    def test_missing_deal_number_gives_no_candidates(self):
        self._create_postlog(network_deal_number=False)
        row = self._search()['rows'][0]
        self.assertEqual(row['status'], 'no_suggestion')

    def test_apply_rejects_stale_filter_context(self):
        postlog = self._create_postlog()
        with self.assertRaises(UserError):
            self.Postlog.fuzzy_match_apply(
                [{'postlog_id': postlog.id, 'schedule_id': self.schedule.id, 'source': 'suggested'}],
                self.program.id,
                date(2026, 8, 3).isoformat(),   # wrong week
            )

    def test_manual_override_must_be_confirmed(self):
        postlog = self._create_postlog()
        with self.assertRaises(UserError):
            self.Postlog.fuzzy_match_apply([{
                'postlog_id': postlog.id,
                'schedule_id': self.other_schedule.id,
                'source': 'manual',
            }], self.program.id, self.week.isoformat())

    # ------------------------------------------------------------------
    # Postlog-data-specific behaviour
    # ------------------------------------------------------------------

    def test_length_selection_is_parsed_without_v_prefix(self):
        """mv.spot_data.length is a Selection (v_30), not a Char ("30")."""
        self.assertEqual(self.Postlog._fuzzy_parse_length('v_30'), 30)
        self.assertEqual(self.Postlog._fuzzy_parse_length('v_120'), 120)
        self.assertEqual(self.Postlog._fuzzy_parse_length('30'), 30)
        self.assertEqual(self.Postlog._fuzzy_parse_length(60), 60)
        self.assertIsNone(self.Postlog._fuzzy_parse_length(False))

        self._create_postlog()
        row = self._search()['rows'][0]
        # The row shows seconds, never the raw selection key.
        self.assertEqual(row['length'], 30)

    def test_length_mismatch_is_detected_across_selection_keys(self):
        self._create_postlog(length='v_60')      # rotation is a :30
        row = self._search()['rows'][0]
        self.assertNotEqual(row['match_quality'], 'exact')

    def test_post_midnight_air_time_matches_overnight_rotation(self):
        """Vendor "XM" times arrive as 00:xx and must match a 12A-3A rotation."""
        overnight = self.env['mv.schedules'].create({
            'deal_parent': self.deal.id,
            'week': self.week,
            'start_time': 'v_12_00a',
            'end_time': 'v_03_00a',
            'days_allowed': [Command.set(self.monday.ids)],
            'rate': 100.0,
            'status': 'sold',
        })
        self._create_postlog(air_time='00:10:56')
        row = self._search()['rows'][0]
        self.assertEqual(row['suggested']['id'], overnight.id)
        self.assertEqual(row['match_quality'], 'exact')

    def test_no_version_or_removed_surface(self):
        self._create_postlog()
        counts = self._search()['counts']
        self.assertNotIn('removed', counts)
        self.assertEqual(
            set(counts), {'all', 'matched', 'unmatched', 'suggestions', 'no_suggestion'},
        )
        options = self.Postlog.fuzzy_match_get_options()
        self.assertNotIn('versions', options)
        self.assertFalse(hasattr(self.Postlog, 'fuzzy_match_set_removed'))

    # ------------------------------------------------------------------
    # Filters, tabs, sorting, export
    # ------------------------------------------------------------------

    def test_workbench_filters_are_independently_optional(self):
        """Each filter is optional and blank means "all".

        Asserted via a unique search term rather than a global row count, so the
        test holds on a database that already contains other Postlog Data.
        """
        marker = 'OptionalFilterMarker-XYZ'
        postlog = self._create_postlog(product=marker)
        for program_id, week in (
            (False, False),
            (self.program.id, False),
            (False, self.week.isoformat()),
            (self.program.id, self.week.isoformat()),
        ):
            result = self.Postlog.fuzzy_match_search(program_id, week, search_term=marker)
            self.assertEqual(
                [row['id'] for row in result['rows']], [postlog.id],
                f"filters program={program_id!r} week={week!r} did not return the row",
            )

    def test_status_tabs_partition_the_rows(self):
        self._create_postlog()                                                   # suggestion
        # A rate or day mismatch is a *suggestion* now, so a genuine dead end
        # needs a deal number that resolves to no schedules at all.
        self._create_postlog(network_deal_number='NOT-FOUND')                    # no_suggestion
        self._create_postlog(schedule=self.schedule.id, import_match_status='matched')

        counts = self._search()['counts']
        self.assertEqual(counts['all'], 3)
        self.assertEqual(counts['matched'], 1)
        self.assertEqual(counts['suggestions'], 1)
        self.assertEqual(counts['no_suggestion'], 1)
        self.assertEqual(counts['unmatched'], 2)
        self.assertEqual(self._search(status='matched')['total'], 1)
        self.assertEqual(self._search(status='unmatched')['total'], 2)

    def test_single_column_sorting_both_directions(self):
        low = self._create_postlog(spot_rate=10.0)
        high = self._create_postlog(spot_rate=500.0)
        asc = self._search(sort_by='rate', sort_direction='asc')['rows']
        desc = self._search(sort_by='rate', sort_direction='desc')['rows']
        self.assertEqual(asc[0]['id'], low.id)
        self.assertEqual(desc[0]['id'], high.id)

    def test_search_term_matches_product_and_deal_and_schedule(self):
        self._create_postlog(schedule=self.schedule.id, import_match_status='matched')
        self.assertEqual(self._search(search_term='SPT-100')['total'], 1)
        self.assertEqual(self._search(search_term='Test Advertiser')['total'], 1)
        self.assertEqual(self._search(search_term='no-such-thing')['total'], 0)

    def test_export_csv_uses_standard_escaping(self):
        self._create_postlog(product='Comma, "Quoted" / Product')
        export = self.Postlog.fuzzy_workbench_export_csv(
            self.program.id, self.week.isoformat()
        )
        self.assertTrue(export['filename'].startswith('PostlogWorkbench-'))
        self.assertNotIn('-v', export['filename'])          # no version segment
        rows = list(csv.reader(io.StringIO(export['content'])))
        self.assertEqual(rows[0][0], 'Postlog Data')
        self.assertIn('Comma, "Quoted" / Product', rows[1])

    # ------------------------------------------------------------------
    # Bulk actions + access
    # ------------------------------------------------------------------

    def test_bulk_attach_skips_non_attachable_rows(self):
        good = self._create_postlog()
        # Not a rate mismatch: that is an attachable fuzzy suggestion now.
        bad = self._create_postlog(network_deal_number='NOT-FOUND')   # no suggestion at all
        result = self.Postlog.fuzzy_workbench_bulk_action(
            'attach',
            {'all_matching': False, 'ids': [good.id, bad.id], 'excluded_ids': []},
            self.program.id,
            self.week.isoformat(),
        )
        self.assertEqual(result.get('attached'), 1)
        self.assertEqual(good.schedule, self.schedule)
        self.assertFalse(bad.schedule)

    def test_bulk_action_rejects_dropped_remove_verbs(self):
        """remove/unremove no longer exist and must not fall through to delete."""
        postlog = self._create_postlog()
        for verb in ('remove', 'unremove'):
            with self.assertRaises(UserError):
                self.Postlog.fuzzy_workbench_bulk_action(
                    verb,
                    {'all_matching': False, 'ids': [postlog.id], 'excluded_ids': []},
                    self.program.id, self.week.isoformat(),
                )
        self.assertTrue(postlog.exists())

    def test_bulk_delete_removes_rows_permanently(self):
        postlog = self._create_postlog()
        result = self.Postlog.fuzzy_workbench_bulk_action(
            'delete',
            {'all_matching': False, 'ids': [postlog.id], 'excluded_ids': []},
            self.program.id, self.week.isoformat(),
        )
        self.assertEqual(result['deleted'], 1)
        self.assertFalse(postlog.exists())

    def test_page_requires_postlog_operator_access(self):
        user = new_test_user(self.env, login='postlog_no_access', groups='base.group_portal')
        with self.assertRaises(UserError):
            self.Postlog.with_user(user).fuzzy_match_get_options()

    # ------------------------------------------------------------------
    # Import job
    # ------------------------------------------------------------------

    def test_reimport_of_an_existing_week_is_blocked(self):
        """One upload per week: refuse rather than replace."""
        self._create_postlog()
        self.env.user.partner_id.email = 'postlog-tests@example.com'
        with self.assertRaises(UserError):
            self.env['mv.postlog_import_job'].create_from_wizard(
                program=self.program,
                upload_file=b'',
                upload_filename='again.csv',
                import_week=self.week,
            )

    def test_import_job_requires_an_email_address(self):
        self.env.user.partner_id.email = False
        with self.assertRaises(UserError):
            self.env['mv.postlog_import_job'].create_from_wizard(
                program=self.program,
                upload_file=b'',
                upload_filename='x.csv',
                import_week=self.week,
            )

    def test_latest_upload_defaults_to_this_users_last_job(self):
        self.env.user.partner_id.email = 'postlog-tests@example.com'
        job = self.env['mv.postlog_import_job'].create({
            'upload_file': b'',
            'upload_filename': 'postlogs.csv',
            'file_checksum': 'abc123',
            'program_id': self.program.id,
            'import_week': self.week,
            'submitted_by_id': self.env.user.id,
            'notification_email': 'postlog-tests@example.com',
            'state': 'completed',
        })
        self._create_postlog(import_job=job.id)
        latest = self.Postlog.fuzzy_match_get_options()['latest_upload']
        self.assertTrue(latest)
        self.assertEqual(latest['id'], job.id)
        self.assertEqual(latest['program_id'], self.program.id)
        self.assertEqual(latest['row_count'], 1)
        self.assertNotIn('version', latest)

    # ==================================================================
    # Coverage added after a gap review. Each test below closes a path
    # that was previously unexercised.
    # ==================================================================

    # ---- bulk selection over every matching row (destructive paths) ----

    def test_bulk_all_matching_spans_pages_and_honors_exclusions(self):
        """all_matching must span pages and must respect excluded_ids.

        This guards the most dangerous path in the workbench: "select all
        matching, except these" feeding into Attach and Delete.
        """
        postlogs = self.Postlog.create([
            {
                'import_program': self.program.id,
                'import_week_value': self.week,
                'broadcast_network': 'Postlog Test Network',
                'network_deal_number': 'SPT-100',
                'air_date': self.week,
                'air_time': '09:30:00',
                'length': 'v_30',
                'spot_rate': 100.0,
                'product': 'Bulk %s' % index,
                'status': 'aired',
                'import_match_status': 'created_without_schedule',
            }
            for index in range(205)
        ])
        page = self._search()
        self.assertEqual(page['total'], 205)
        self.assertEqual(len(page['rows']), 200)

        excluded = postlogs[-1]
        attached = self.Postlog.fuzzy_workbench_bulk_action(
            'attach',
            {'all_matching': True, 'ids': [], 'excluded_ids': [excluded.id]},
            self.program.id,
            self.week.isoformat(),
        )
        self.assertEqual(attached['attached'], 204)
        self.assertEqual(len(postlogs.filtered(lambda s: s.schedule)), 204)
        self.assertFalse(excluded.schedule)

        deleted = self.Postlog.fuzzy_workbench_bulk_action(
            'delete',
            {'all_matching': True, 'ids': [], 'excluded_ids': [excluded.id]},
            self.program.id,
            self.week.isoformat(),
        )
        self.assertEqual(deleted['deleted'], 204)
        self.assertTrue(excluded.exists())
        self.assertEqual(
            self.Postlog.search_count([('import_program', '=', self.program.id)]), 1
        )

    def test_bulk_fuzzy_attach_requires_confirmation_before_writing(self):
        """A buffer-only (non-exact) match must not be bulk-attached silently."""
        postlog = self._create_postlog(air_time='11:00:00')       # inside buffer, outside rotation
        selection = {'all_matching': False, 'ids': [postlog.id], 'excluded_ids': []}

        preview = self.Postlog.fuzzy_workbench_bulk_action(
            'attach', selection, self.program.id, self.week.isoformat(),
            confirmed_fuzzy=False,
        )
        self.assertTrue(preview['requires_confirmation'])
        self.assertEqual(preview['fuzzy'], 1)
        self.assertEqual(preview['selected'], 1)
        self.assertEqual(preview['attachable'], 1)
        self.assertNotIn('attached', preview)   # nothing was written
        self.assertFalse(postlog.schedule)

        applied = self.Postlog.fuzzy_workbench_bulk_action(
            'attach', selection, self.program.id, self.week.isoformat(),
            confirmed_fuzzy=True,
        )
        self.assertEqual(applied['attached'], 1)
        self.assertEqual(postlog.schedule, self.schedule)

    # ---- schedule length resolution ------------------------------------

    def test_zero_unitlength_falls_back_to_deal_length(self):
        """Every real schedule has unitlength = 0, so the fallback is load-bearing."""
        self.schedule.unitlength = 0
        self.assertEqual(self.Postlog._fuzzy_schedule_length(self.schedule), 30)
        self._create_postlog(length='v_30')
        self.assertEqual(self._search()['rows'][0]['match_quality'], 'exact')

    def test_populated_unitlength_overrides_deal_length(self):
        pm_schedule = self.env['mv.schedules'].create({
            'deal_parent': self.deal.id,          # deal length is v_30
            'week': self.week,
            'start_time': 'v_02_00p',
            'end_time': 'v_03_00p',
            'days_allowed': [Command.set(self.monday.ids)],
            'rate': 100.0,
            'status': 'sold',
            'unitlength': 60,                     # overrides the deal's 30
        })
        self.assertEqual(self.Postlog._fuzzy_schedule_length(pm_schedule), 60)
        self._create_postlog(air_time='14:30:00', length='v_60')
        row = self._search()['rows'][0]
        self.assertEqual(row['suggested']['id'], pm_schedule.id)
        self.assertEqual(row['match_quality'], 'exact')

    # ---- ambiguity -----------------------------------------------------

    def test_tied_schedules_are_reported_as_ambiguous(self):
        twin = self.env['mv.schedules'].create({
            'deal_parent': self.deal.id,
            'week': self.week,
            'start_time': 'v_09_00a',
            'end_time': 'v_10_00a',
            'days_allowed': [Command.set(self.monday.ids)],
            'rate': 100.0,
            'status': 'sold',
        })
        postlog = self._create_postlog()
        row = self._search()['rows'][0]
        self.assertGreaterEqual(row['ambiguous_count'], 2)
        self.assertIn(row['suggested']['id'], (self.schedule.id, twin.id))
        self.assertTrue(row['reason'])

        # the "Tied schedules" issue filter must surface it
        filtered = self._search(issue_filter='ambiguous')
        self.assertEqual([r['id'] for r in filtered['rows']], [postlog.id])

    # ---- pagination ----------------------------------------------------

    def test_pagination_spans_pages_and_clamps_offset(self):
        self.Postlog.create([
            {
                'import_program': self.program.id,
                'import_week_value': self.week,
                'network_deal_number': 'SPT-100',
                'broadcast_network': 'Postlog Test Network',
                'air_date': self.week,
                'air_time': '09:30:00',
                'length': 'v_30',
                'spot_rate': 100.0,
                'product': 'Page %s' % index,
                'status': 'aired',
                'import_match_status': 'created_without_schedule',
            }
            for index in range(205)
        ])
        first = self._search(offset=0)
        self.assertEqual(first['total'], 205)
        self.assertEqual(len(first['rows']), 200)
        self.assertEqual(first['page'], 1)
        self.assertEqual(first['pages'], 2)

        second = self._search(offset=200)
        self.assertEqual(len(second['rows']), 5)
        self.assertEqual(second['page'], 2)

        # an offset past the end must clamp back onto the last page
        clamped = self._search(offset=10_000)
        self.assertEqual(clamped['offset'], 200)
        self.assertEqual(len(clamped['rows']), 5)

        # no overlap between the two pages
        self.assertFalse(
            {r['id'] for r in first['rows']} & {r['id'] for r in second['rows']}
        )

    # ---- program isolation ---------------------------------------------

    def test_search_is_scoped_to_the_selected_program(self):
        mine = self._create_postlog()
        theirs = self._create_postlog(import_program=self.other_program.id)

        self.assertEqual([r['id'] for r in self._search()['rows']], [mine.id])
        other = self.Postlog.fuzzy_match_search(
            self.other_program.id, self.week.isoformat()
        )
        self.assertEqual([r['id'] for r in other['rows']], [theirs.id])

    def test_cannot_attach_a_schedule_from_another_program(self):
        postlog = self._create_postlog()
        with self.assertRaises(UserError):
            self.Postlog.fuzzy_match_apply([{
                'postlog_id': postlog.id,
                'schedule_id': self.other_schedule.id,
                'source': 'suggested',
            }], self.program.id, self.week.isoformat())
        self.assertFalse(postlog.schedule)

    # ---- import job failure paths --------------------------------------

    def _make_job(self, **overrides):
        values = {
            'upload_file': b'',
            'upload_filename': 'postlogs.csv',
            'file_checksum': 'chk-%s' % (overrides.get('file_checksum') or 'x'),
            'program_id': self.program.id,
            'import_week': self.week,
            'submitted_by_id': self.env.user.id,
            'notification_email': 'postlog-tests@example.com',
        }
        values.update(overrides)
        return self.env['mv.postlog_import_job'].create(values)

    def test_job_failure_is_recorded_and_does_not_raise(self):
        """A bad upload must land as state=failed with a message, not explode."""
        import base64
        job = self._make_job(
            upload_file=base64.b64encode(b'not,a,real,postlog\n'),
            upload_filename='broken.csv',
        )
        job._run_job()                      # must not raise
        self.assertEqual(job.state, 'failed')
        self.assertTrue(job.failure_message)
        self.assertTrue(job.finished_at)
        self.assertFalse(self.Postlog.search_count([('import_job', '=', job.id)]))

    def test_queued_job_is_picked_up_by_the_cron_entry_point(self):
        import base64
        job = self._make_job(
            upload_file=base64.b64encode(b'nothing\n'),
            upload_filename='broken.csv',
        )
        self.assertEqual(job.state, 'queued')
        self.env['mv.postlog_import_job']._cron_process_postlog_import_jobs()
        self.assertIn(job.state, ('completed', 'failed'))

    def test_identical_queued_upload_is_not_duplicated(self):
        self.env.user.partner_id.email = 'postlog-tests@example.com'
        # no Postlog Data for a different week, so create_from_wizard is allowed
        other_week = date(2026, 8, 3)
        first, created_first = self.env['mv.postlog_import_job'].create_from_wizard(
            program=self.program,
            upload_file=b'',
            upload_filename='dup.csv',
            import_week=other_week,
        )
        self.assertTrue(created_first)
        second, created_second = self.env['mv.postlog_import_job'].create_from_wizard(
            program=self.program,
            upload_file=b'',
            upload_filename='dup.csv',
            import_week=other_week,
        )
        self.assertFalse(created_second)
        self.assertEqual(first, second)

    # ---- engine parse-error collection ---------------------------------

    def test_engine_collects_parse_errors_instead_of_aborting(self):
        """One malformed cell must not cost the operator the whole upload."""
        from ..services.postlog_import.engine import PostlogImportEngine
        engine = PostlogImportEngine(
            self.env,
            program=self.program,
            upload_file=b'',
            upload_filename='postlogs.csv',
        )
        vals = engine.build_row_vals(
            {
                'air_date': 'not-a-date',
                'air_time': '09:30:00',
                'network_deal_number': 'SPT-100',
                'length': '1:00',
                'spot_rate': '100',
            },
            self.week,
            2,
        )
        self.assertFalse(vals['air_date'])
        self.assertTrue(vals['import_match_detail'])
        self.assertEqual(vals['import_match_status'], 'created_without_schedule')
        # the rest of the row still came through
        self.assertEqual(vals['network_deal_number'], 'SPT-100')
        self.assertEqual(vals['length'], 'v_60')
        self.assertEqual(vals['import_program'], self.program.id)
        self.assertEqual(vals['import_week_value'], self.week)

    def test_engine_sets_import_program_and_week_on_every_row(self):
        from ..services.postlog_import.engine import PostlogImportEngine
        engine = PostlogImportEngine(
            self.env,
            program=self.program,
            upload_file=b'',
            upload_filename='postlogs.csv',
        )
        vals = engine.build_row_vals(
            {
                'air_date': '07/27/26',
                'air_time': '09:30:00',
                'network_deal_number': 'SPT-100',
                'length': ':30',
                'spot_rate': '100',
            },
            self.week,
            2,
        )
        self.assertEqual(vals['import_program'], self.program.id)
        self.assertEqual(vals['import_week_value'], self.week)
        self.assertEqual(vals['length'], 'v_30')
        self.assertEqual(vals['import_match_status'], 'matched')
        self.assertTrue(vals['schedule'])

    # ---- access --------------------------------------------------------

    def test_internal_user_without_the_operator_group_is_refused(self):
        user = new_test_user(
            self.env, login='postlog_plain_user', groups='base.group_user',
        )
        with self.assertRaises(UserError):
            self.Postlog.with_user(user).fuzzy_match_get_options()


@tagged('post_install', '-at_install')
class TestPostlogImportRouting(TransactionCase):
    """The Import Postlog wizard routes on mv.programs.cable_synd (Program Type).

    Cable -> our engine. Bundle/PP -> phase28. Digital/GM/Syndication and a
    blank Program Type are refused rather than guessed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env['mv.postlog.upload.wizard']
        cls.program = cls.env['mv.programs'].create({
            'name': 'Routing Test Network',
            'clientcode': 'RTN',
        })

    def _probe(self, program_type, program=None):
        program = program or self.program
        program.cable_synd = program_type
        wizard = self.Wizard.new({
            'program_id': program.id,
            'program_choice': str(program.id),
        })
        wizard._compute_route()
        return wizard

    def test_cable_routes_to_our_engine(self):
        w = self._probe('cable')
        self.assertEqual(w.route, 'postlog')
        self.assertTrue(w.can_import)

    def test_pp_routes_to_phase28_paid_programming(self):
        w = self._probe('pp')
        self.assertEqual(w.route, 'bundle')
        self.assertTrue(w.can_import)
        self.assertEqual(w._bundle_code(), 'paid_programming')

    def test_known_bundle_program_maps_to_its_phase28_code(self):
        asc = self.env['mv.programs'].create({
            'name': 'American Spirit Connect',
            'clientcode': 'ASCX',
        })
        w = self._probe('bundle', program=asc)
        self.assertEqual(w.route, 'bundle')
        self.assertTrue(w.can_import)
        self.assertEqual(w._bundle_code(), 'american_spirit')

    def test_unmapped_bundle_program_is_blocked_not_guessed(self):
        """A rename in prod must fail loudly, never route to the wrong handler."""
        w = self._probe('bundle')          # "Routing Test Network" is not mapped
        self.assertEqual(w.route, 'unmapped')
        self.assertFalse(w.can_import)
        self.assertFalse(w._bundle_code())
        with self.assertRaises(UserError):
            w.action_import()

    def test_blank_program_type_is_blocked_with_a_useful_message(self):
        w = self._probe(False)
        self.assertEqual(w.route, 'unset')
        self.assertFalse(w.can_import)
        self.assertIn('Program Type', w.route_message)
        self.assertIn(self.program.display_name, w.route_message)

    def test_unbuilt_program_types_are_blocked(self):
        for program_type in ('digital', 'gm', 'syndication'):
            w = self._probe(program_type)
            self.assertEqual(w.route, 'unsupported', program_type)
            self.assertFalse(w.can_import, program_type)
            self.assertIn('not been built yet', w.route_message)

    def test_action_import_refuses_a_blocked_route_server_side(self):
        """The view hides the button, but the method must guard too."""
        w = self._probe('syndication')
        w.upload_file = b''
        with self.assertRaises(UserError):
            w.action_import()
