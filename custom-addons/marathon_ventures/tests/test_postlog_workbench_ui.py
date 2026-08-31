# -*- coding: utf-8 -*-
"""Browser tests for the Postlog Workbench client action.

The Python service tests cover the RPCs; nothing there proves the OWL component
actually compiles and mounts. These run the real page in headless Chrome and
fail on any JavaScript console error, which is the only way to catch a broken
QWeb template, a missing t-key, or a handler that no longer exists.

Requires a Chrome/Chromium binary on PATH under one of the names Odoo looks for
('google-chrome', 'chromium', 'chromium-browser', 'google-chrome-stable').
Odoo skips these tests when none is found.
"""
from datetime import date

from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestPostlogWorkbenchUI(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.week = date(2026, 7, 27)
        cls.program = cls.env['mv.programs'].create({
            'name': 'UI Test Network',
            'clientcode': 'UIT',
            'clock_start_time': 'v_6am',
        })
        monday = cls.env['mv.days_allowed.tag'].search(
            [('name', '=ilike', 'Mon%')], limit=1,
        )
        if not monday:
            monday = cls.env['mv.days_allowed.tag'].create({'name': 'Mon'})
        deal = cls.env['mv.deal'].create({
            'program': cls.program.id,
            'network_deal_number': 'UIT-1',
            'length': 'v_30',
        })
        cls.schedule = cls.env['mv.schedules'].create({
            'deal_parent': deal.id,
            'week': cls.week,
            'start_time': 'v_09_00a',
            'end_time': 'v_10_00a',
            'days_allowed': [Command.set(monday.ids)],
            'rate': 100.0,
            'status': 'sold',
        })
        cls.postlog = cls.env['mv.spot_data'].create({
            'import_program': cls.program.id,
            'import_week_value': cls.week,
            'broadcast_network': 'UI Test Network',
            'network_deal_number': 'UIT-1',
            'air_date': cls.week,
            'air_time': '09:30:00',
            'length': 'v_30',
            'spot_rate': 100.0,
            'product': 'UI Fixture Product',
            'status': 'aired',
            'import_match_status': 'created_without_schedule',
        })
        cls.action = cls.env.ref('marathon_ventures.action_mv_postlog_workbench')

    def test_workbench_tour(self):
        """Mount the client action and drive it end to end in a real browser.

        Covers what the Python tests cannot: that the OWL template compiles and
        mounts, that the dropped Version filter and Removed tab really are gone
        from the DOM, that the filters fire a real RPC, and that a matched row
        with its deal number and suggested schedule reaches the page.

        Fails on any uncaught JavaScript error. Skipped automatically when no
        Chrome/Chromium binary is on PATH.
        """
        action = self.env.ref('marathon_ventures.action_mv_postlog_workbench')
        self.start_tour(
            '/odoo/action-%s' % action.id,
            'postlog_workbench_tour',
            login='admin',
        )
