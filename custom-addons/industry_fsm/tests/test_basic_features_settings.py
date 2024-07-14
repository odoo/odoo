# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.tests import Form, tagged

from odoo.addons.project.tests.test_project_base import TestProjectCommon


@tagged('-at_install', 'post_install')
class TestBasicFeaturesSettings(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project_pigs.write({
            'is_fsm': True,
        })

    def test_basic_features(self):
        for config_flag, project_flag in (
            ('group_project_task_dependencies', 'allow_task_dependencies'),
            ('group_project_milestone', 'allow_milestones'),
        ):
            self._test_basic_feature(config_flag, project_flag)

    def _test_basic_feature(self, config_flag, project_flag):
        self.env["res.config.settings"].create({config_flag: True}).execute()

        self.assertFalse(self.project_pigs[project_flag], f"FSM Projects should not follow {config_flag} setting changes")

        with self.debug_mode():
            # <div class="col-lg-6 o_setting_box" groups="base.group_no_one">
            #     <div class="o_setting_left_pane">
            #         <field name="is_fsm"/>
            #     </div>
            with Form(self.env['project.project']) as project_form:
                project_form.name = 'My Ducks Project'
                project_form.is_fsm = True
                self.assertFalse(project_form[project_flag], f"The {project_flag} feature should be disabled by default on new FSM projects")

        self.project_pigs.write({project_flag: True})
        self.assertTrue(self.project_pigs[project_flag], f"The {project_flag} feature should be enabled on the project")

        self.env["res.config.settings"].create({config_flag: False}).execute()
        self.assertFalse(self.project_pigs[project_flag], "The feature should be disabled on the FSM project when disabled globally")
