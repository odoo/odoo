# -*- coding: utf-8 -*-

# import datetime
# from dateutil.relativedelta import relativedelta

from openerp.addons.crm.tests.common import TestCrmCommon
# from openerp.exceptions import AccessError, ValidationError, Warning
# from openerp.tools import mute_logger


class TestCrmStages(TestCrmCommon):

    # @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_stages_access_rights(self):
        """ Stage access rights """
        test_stage = self.Stage.sudo(self.user_salemanager).create({
            'name': 'TestDuplicated',
            'default': 'copy',
        })

        test_stage.unlink()

    def test_10_team_fixed_stages(self):
        """ Sales team with fixed stages """
        team = self.SalesTeam.sudo(self.user_salemanager).create({
            'name': 'Test0',
            'stage_ids': [self.stage_none_1.id],
        })

        self.assertEqual(
            team.stage_ids, self.stage_none_1,
            'crm: wrong behavior of stages, new team with fixed stages should get them')

    def test_11_team_default_stages(self):
        """ Create a new sales team, check its stages, should be default ones """
        SalesTeamManager = self.SalesTeam.sudo(self.user_salemanager)
        st_1 = SalesTeamManager.create({
            'name': 'Test SalesTeam 1',
        })
        self.assertEqual(
            len(st_1.stage_ids), 2,
            'crm: wrong general behavior of columns, should have 1 shared and 1 duplicated column')
        self.assertIn(
            self.stage_link_1, st_1.stage_ids,
            'crm: wrong behavior of link columns')
        self.assertEqual(
            set(['link', 'specific']),
            set([stage.default for stage in st_1.stage_ids]),
            'crm: wrong behavior of copied /shared columns')
        self.assertEqual(
            set([self.stage_link_1.name, self.stage_copy_1.name]),
            set([stage.name for stage in st_1.stage_ids]),
            'crm: wrong behavior of copied / shared columns')
        self.assertNotIn(
            self.stage_copy_1,
            st_1.stage_ids,
            'crm: wrong behavior of copied columns')

    def test_12_team_all(self):
        """ Full power of the mega death"""
        SalesTeamManager = self.SalesTeam.sudo(self.user_salemanager)
        st_1 = SalesTeamManager.create({
            'name': 'Test SalesTeam 1',
            'stage_ids': [
                (4, self.stage_link_1.id),
                (4, self.stage_copy_1.id),
                (3, self.stage_none_1.id),
                (1, self.stage_specific_1.id, {'default': 'link'}),
                (0, 0, {'name': 'EmbedCopy', 'default': 'copy'}),
                (0, 0, {'name': 'Embed', 'default': 'none'}),
            ]
        })
        self.assertIn(
            self.stage_link_1, st_1.stage_ids,
            'crm: shared column should be present')
        self.assertNotIn(
            self.stage_copy_1, st_1.stage_ids,
            'crm: copied column should not be present')
        self.assertNotIn(
            self.stage_none_1, st_1.stage_ids,
            'crm: removal command should not link a stage')
        self.assertIn(
            self.stage_specific_1, st_1.stage_ids,
            'crm: specific -> shared column should be present')
        print st_1.stage_ids
