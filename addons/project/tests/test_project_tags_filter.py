# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, HttpCase
from odoo import Command
from .test_project_base import TestProjectCommon


@tagged('-at_install', 'post_install')
class TestProjectTags(HttpCase, TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['project.tags'].create([
            {'name': 'Corkscrew tailed', 'project_ids': [Command.link(cls.project_pigs.id)]},
            {'name': 'Horned', 'project_ids': [Command.link(cls.project_goats.id)]},
            {
                'name': '4 Legged',
                'project_ids': [
                    Command.link(cls.project_goats.id),
                    Command.link(cls.project_pigs.id),
                ],
            },
        ])

        cls.project_pigs.write({
            'stage_id': cls.env['project.project.stage'].create({
                'name': 'pig stage',
            }).id,
        })
        cls.project_goats.write({
            'stage_id': cls.env['project.project.stage'].create({
                'name': 'goat stage',
            }).id,
        })

        cls.env["res.config.settings"].create({'group_project_stages': True}).execute()

        cls.env['ir.filters'].create([
            {
                'name': 'Corkscrew tail tag filter',
                'model_id': 'project.project',
                'domain': '[("tag_ids", "ilike", "Corkscrew")]',
            },
            {
                'name': 'horned tag filter',
                'model_id': 'project.project',
                'domain': '[("tag_ids", "ilike", "horned")]',
            },
            {
                'name': '4 Legged tag filter',
                'model_id': 'project.project',
                'domain': '[("tag_ids", "ilike", "4 Legged")]',
            },
        ])

    def test_01_project_tags(self):
        self.start_tour("/odoo", 'project_tags_filter_tour', login="admin")
