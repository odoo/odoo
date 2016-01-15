# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .test_project_base import TestProjectBase


class TestProjectArchive(TestProjectBase):

    @classmethod
    def setUpClass(cls):
        super(TestProjectArchive, cls).setUpClass()

        # Columns
        cls.stage_10 = cls.env['project.task.type'].create({
            'name': 'Stage1',
            'sequence': 1,
        })
        cls.stage_11 = cls.env['project.task.type'].create({
            'name': 'Stage2',
            'sequence': 2,
        })
        cls.project_pigs.write({'type_ids': [(5), (4, cls.stage_10.id), (4, cls.stage_11.id)]})
        cls.task_1.write({
            'stage_id': cls.stage_10.id
        })
        cls.task_2.write({
            'stage_id': cls.stage_11.id
        })

    def test_project_archive_stage_own_all(self):
        """ Archive stages specific to a project. Check that other stages are
        untouched. """
        self.assertEqual(
            self.project_pigs.type_ids,
            self.stage_10 | self.stage_11)

        self.project_pigs.archive_stages(True, stage_ids=None)
        self.project_pigs.invalidate_cache()

        Stage = self.env['project.task.type']
        self.assertEqual(
            self.project_pigs.type_ids,
            Stage)
        other_stages = Stage.search([('id', 'in', [self.stage_0.id, self.stage_1.id, self.stage_10.id, self.stage_11.id])])
        self.assertEqual(
            other_stages,
            self.stage_0 | self.stage_1)
        self.assertEqual(
            self.project_pigs.tasks,
            self.env['project.task'])

    def test_project_archive_stage_own_limited(self):
        """ Archive stages specific to a project. Check that other stages are
        untouched. """
        self.assertEqual(
            self.project_pigs.type_ids,
            self.stage_10 | self.stage_11)

        self.project_pigs.archive_stages(True, stage_ids=[self.stage_11.id])
        self.project_pigs.invalidate_cache()

        Stage = self.env['project.task.type']
        self.assertEqual(
            self.project_pigs.type_ids,
            self.stage_10)
        other_stages = Stage.search([('id', 'in', [self.stage_0.id, self.stage_1.id, self.stage_10.id, self.stage_11.id])])
        self.assertEqual(
            other_stages,
            self.stage_0 | self.stage_1 | self.stage_10)
        self.assertEqual(
            self.project_pigs.tasks,
            self.task_1)

    def test_project_archive_stage_own_shared(self):
        """ Archive stages of a project with one specific. This one should still
        be active. Other stages are intouched. """
        self.project_goats.write({'type_ids': [(4, self.stage_10.id)]})

        self.project_pigs.archive_stages(True, stage_ids=None)
        self.project_pigs.invalidate_cache()

        Stage = self.env['project.task.type']
        self.assertEqual(
            self.project_pigs.type_ids,
            self.stage_10)
        other_stages = Stage.search([('id', 'in', [self.stage_0.id, self.stage_1.id, self.stage_10.id, self.stage_11.id])])
        self.assertEqual(
            other_stages,
            self.stage_0 | self.stage_1 | self.stage_10)
        self.assertEqual(
            self.project_pigs.tasks,
            self.env['project.task'])

    def test_project_archive_multiple(self):
        """ Archive stages of several projects. All should be archived. """
        self.project_goats.write({'type_ids': [(4, self.stage_1.id)]})

        Stage = self.env['project.task.type']
        projects = self.project_pigs | self.project_goats
        projects.write({'active': False})
        projects.invalidate_cache()

        self.assertEqual(
            self.project_pigs.type_ids,
            Stage)
        self.assertEqual(
            self.project_goats.type_ids,
            Stage)
        other_stages = Stage.search([('id', 'in', [self.stage_0.id, self.stage_1.id, self.stage_10.id, self.stage_11.id])])
        self.assertEqual(other_stages, Stage)
