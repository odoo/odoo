from unittest.mock import patch

from freezegun import freeze_time

from odoo.exceptions import AccessError, ValidationError
from odoo.modules import module
from odoo.tests import TransactionCase, new_test_user


class TestWebTutorial(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login='tuto_user', groups='base.group_user,base.group_partner_manager')
        cls.env['ir.config_parameter'].sudo().set_str('database.expiration_reason', 'trial')
        cls.partner_action = cls.env['ir.actions.act_window'].create({
            'name': 'Tuto Partners', 'res_model': 'res.partner', 'path': 'tuto-partners',
        })
        cls.tutorial = cls.env['web_tutorial.tutorial'].create({'action_id': cls.partner_action.id, 'name': 'test_tutorial'})
        cls.chapter = cls.env['web_tutorial.chapter'].create({
            'tutorial_id': cls.tutorial.id,
            'model_id': cls.env['ir.model']._get_id('res.partner'),
            'view_type': 'form',
        })
        cls.email_step, cls.phone_step = cls.env['web_tutorial.step'].create([
            {'chapter_id': cls.chapter.id, 'type': 'field', 'name': 'email', 'content': "Fill in the email"},
            {'chapter_id': cls.chapter.id, 'type': 'field', 'name': 'phone', 'content': "Fill in the phone"},
        ])

    def get_running_tutorials(self, user=None):
        """ Return the running tutorials created by these tests """
        with patch.object(module, 'current_test', None):
            tutorials = self.env['web_tutorial.tutorial'].with_user(user or self.user).get_running_tutorials()
        return [tutorial for tutorial in tutorials if tutorial['name'] in ('test_tutorial', 'cron_tutorial')]

    def test_only_started_tutorials_run_outside_trial(self):
        self.env['ir.config_parameter'].sudo().set_str('database.expiration_reason', 'renewal')
        self.assertEqual(self.get_running_tutorials(), [])
        tutorial = self.tutorial.with_user(self.user)
        tutorial.action_restart()
        self.assertEqual([tutorial['name'] for tutorial in self.get_running_tutorials()], ['test_tutorial'])
        tutorial.mark_done()
        self.assertEqual(self.get_running_tutorials(), [])
        tutorial.action_restart()
        self.tutorial.active = False
        self.assertEqual(self.get_running_tutorials(), [])

    def test_invalid_steps_ignored(self):
        other_tutorial = self.env['web_tutorial.tutorial'].create({'action_id': self.partner_action.id, 'name': 'other_tutorial'})
        other_step = self.env['web_tutorial.step'].create({
            'chapter_id': self.env['web_tutorial.chapter'].create({
                'tutorial_id': other_tutorial.id,
                'model_id': self.env['ir.model']._get_id('res.partner'),
                'view_type': 'form',
            }).id,
            'type': 'field',
            'name': 'name',
            'content': "Name it",
        })
        tutorial = self.tutorial.with_user(self.user)
        tutorial.mark_steps_done(self.email_step.id)
        tutorial.mark_steps_done([str(self.email_step.id)])
        tutorial.mark_steps_done([other_step.id, 0])
        self.assertFalse(tutorial._get_user_progress().done_step_ids)

    def test_no_tutorial_during_tests(self):
        Tutorial = self.env['web_tutorial.tutorial'].with_user(self.user)
        self.assertEqual(Tutorial.get_running_tutorials(), [])
        with patch.object(module, 'current_test', None):
            self.assertTrue(Tutorial.get_running_tutorials())

    def test_one_running_tutorial_by_module(self):
        second_tutorial, first_tutorial = self.env['web_tutorial.tutorial'].create([
            {'action_id': self.partner_action.id, 'name': 'second_tutorial', 'sequence': 2},
            {'action_id': self.partner_action.id, 'name': 'first_tutorial', 'sequence': 1},
        ])
        self.env['ir.model.data'].create([
            {'module': 'tuto_module', 'name': tutorial.name, 'model': tutorial._name, 'res_id': tutorial.id}
            for tutorial in second_tutorial + first_tutorial
        ])

        def get_running_names():
            with patch.object(module, 'current_test', None):
                tutorials = self.env['web_tutorial.tutorial'].with_user(self.user).get_running_tutorials()
            return [tutorial['name'] for tutorial in tutorials if tutorial['name'] in ('first_tutorial', 'second_tutorial')]

        self.assertEqual(get_running_names(), ['first_tutorial'])
        with freeze_time('2026-01-01 10:00:00'):
            second_tutorial.with_user(self.user).action_restart()
        self.assertEqual(get_running_names(), ['second_tutorial'])
        with freeze_time('2026-01-01 11:00:00'):
            first_tutorial.with_user(self.user).action_restart()
        self.assertEqual(get_running_names(), ['first_tutorial'])
        first_tutorial.with_user(self.user).mark_done()
        self.assertEqual(get_running_names(), ['second_tutorial'])

    def test_portal_user_has_no_progress(self):
        portal = new_test_user(self.env, login='tuto_portal', groups='base.group_portal')
        tutorial = self.tutorial.with_user(portal)
        tutorial.mark_done()
        tutorial.mark_steps_done(self.email_step.ids)
        tutorial.mark_steps_undone(self.email_step.ids)
        self.assertFalse(self.env['web_tutorial.tutorial.user'].search([('user_id', '=', portal.id)]))

    def test_progress(self):
        tutorial = self.tutorial.with_user(self.user)
        tutorial.mark_steps_done([self.email_step.id, self.phone_step.id])
        tutorial.mark_steps_done(self.email_step.ids)
        self.assertEqual(self.get_running_tutorials()[0]['done_steps'], [self.email_step.id, self.phone_step.id])

        tutorial.mark_steps_undone(self.email_step.ids)
        self.assertEqual(self.get_running_tutorials()[0]['done_steps'], self.phone_step.ids)

        tutorial.mark_done()
        self.assertEqual(self.get_running_tutorials(), [])

    def test_progress_is_private(self):
        tutorial = self.tutorial.with_user(self.user)
        tutorial.mark_steps_done(self.email_step.ids)
        tutorial.mark_done()
        self.assertEqual(self.tutorial.write_uid, self.env.user)
        progress = tutorial._get_user_progress()
        self.assertTrue(progress.done)
        self.assertEqual(progress.done_step_ids, self.email_step)
        other_user = new_test_user(self.env, login='other_tuto_user', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.env['web_tutorial.tutorial.user'].with_user(other_user).search([])

    def test_restart(self):
        tutorial = self.tutorial.with_user(self.user)
        tutorial.mark_steps_done(self.email_step.ids)
        tutorial.mark_done()
        self.assertEqual(self.get_running_tutorials(), [])

        action = tutorial.action_restart()
        self.assertEqual(action['tag'], 'reload')
        self.assertEqual(action['params']['action_id'], self.partner_action.id)
        self.assertFalse(tutorial._get_user_progress().done_step_ids)
        self.assertEqual(len(self.get_running_tutorials()), 1)

    def test_running_tutorials_access(self):
        cron_action = self.env['ir.actions.act_window'].create({'name': 'Tuto Crons', 'res_model': 'ir.cron'})
        cron_tutorial = self.env['web_tutorial.tutorial'].create({'action_id': cron_action.id, 'name': 'cron_tutorial'})
        admin = self.env.ref('base.user_admin')
        self.assertEqual([tutorial['name'] for tutorial in self.get_running_tutorials()], ['test_tutorial'])
        cron_tutorial.with_user(self.user).mark_done()
        self.assertFalse(cron_tutorial.with_user(self.user)._get_user_progress())
        self.assertEqual(
            [tutorial['name'] for tutorial in self.get_running_tutorials(admin)],
            ['cron_tutorial', 'test_tutorial'],
        )

        self.tutorial.group_ids = self.env.ref('base.group_system')
        self.assertEqual(self.get_running_tutorials(), [])
        tutorial = self.tutorial.with_user(self.user)
        with self.assertRaises(AccessError):
            tutorial.action_restart()
        tutorial.mark_steps_done(self.email_step.ids)
        self.assertFalse(tutorial._get_user_progress())
        self.tutorial.group_ids = self.env.ref('base.group_user')
        self.assertEqual([tutorial['name'] for tutorial in self.get_running_tutorials()], ['test_tutorial'])

        self.partner_action.group_ids = self.env.ref('base.group_system')
        self.assertEqual(self.get_running_tutorials(), [])
        self.assertIn('test_tutorial', [tutorial['name'] for tutorial in self.get_running_tutorials(admin)])

    def test_running_tutorial_chapters(self):
        self.assertFalse(self.get_running_tutorials()[0]['always_show_tooltip'])
        self.tutorial.always_show_tooltip = True
        self.assertTrue(self.get_running_tutorials()[0]['always_show_tooltip'])
        self.chapter.context = "{'default_is_company': True}"
        action = self.create_server_action()
        delete_step, action_step = self.env['web_tutorial.step'].create([
            {'chapter_id': self.chapter.id, 'type': 'generic_button', 'name': 'Delete', 'content': "Delete it", 'hint': True},
            {'chapter_id': self.chapter.id, 'type': 'server_action', 'name': 'web_tutorial.test_action', 'content': "Run it"},
        ])
        step_json = {'action_name': "", 'hint': False}
        self.assertEqual(self.get_running_tutorials()[0]['chapters'], [{
            'context': {'default_is_company': True},
            'id': self.chapter.id,
            'model': 'res.partner',
            'steps': [
                {**step_json, 'content': "Fill in the email", 'id': self.email_step.id, 'name': 'email', 'type': 'field'},
                {**step_json, 'content': "Fill in the phone", 'id': self.phone_step.id, 'name': 'phone', 'type': 'field'},
                {
                    **step_json, 'content': "Delete it", 'hint': True, 'id': delete_step.id, 'name': 'Delete',
                    'type': 'generic_button',
                },
                {
                    **step_json, 'action_name': action.name, 'content': "Run it", 'id': action_step.id,
                    'name': 'web_tutorial.test_action', 'type': 'server_action',
                },
            ],
            'view_type': 'form',
        }])

    def create_server_action(self, model='res.partner', name='test_action'):
        """ Return a server action bound to the model, with an xmlid in web_tutorial """
        action = self.env['ir.actions.server'].create({
            'name': "Tuto Action",
            'model_id': self.env['ir.model']._get_id(model),
            'binding_model_id': self.env['ir.model']._get_id(model),
            'state': 'code',
            'code': "",
        })
        self.env['ir.model.data'].create({'module': 'web_tutorial', 'name': name, 'model': action._name, 'res_id': action.id})
        return action

    def test_step_names(self):
        Step = self.env['web_tutorial.step']
        values = {'chapter_id': self.chapter.id, 'content': "Do it"}
        self.create_server_action()
        self.create_server_action(model='res.users', name='other_model_action')
        self.create_server_action(name='unbound_action').binding_model_id = False
        Step.create({**values, 'type': 'field', 'name': 'child_ids.email'})
        Step.create({**values, 'type': 'method', 'name': 'write'})
        Step.create({**values, 'type': 'server_action', 'name': 'web_tutorial.test_action'})
        for button in ('New', 'Delete', 'Duplicate', 'Archive', 'Unarchive'):
            Step.create({**values, 'type': 'generic_button', 'name': button})
        for invalid in [
            {'type': 'field', 'name': 'no_such_field'},
            {'type': 'field', 'name': 'parent_id.email'},
            {'type': 'field', 'name': 'child_ids.no_such_field'},
            {'type': 'method', 'name': 'no_such_method'},
            {'type': 'method', 'name': '_compute_display_name'},
            {'type': 'server_action', 'name': 'web_tutorial.no_such_action'},
            {'type': 'server_action', 'name': 'web_tutorial.other_model_action'},
            {'type': 'server_action', 'name': 'web_tutorial.unbound_action'},
            {'type': 'server_action', 'name': 'base.model_res_partner'},
            {'type': 'generic_button', 'name': 'Save'},
            {'type': 'generic_button', 'name': 'Edit'},
        ]:
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                Step.create({**values, **invalid})

        chapter_values = {'tutorial_id': self.tutorial.id, 'model_id': self.env['ir.model']._get_id('res.partner')}
        kanban_chapter, list_chapter = self.env['web_tutorial.chapter'].create([
            {**chapter_values, 'view_type': 'kanban'},
            {**chapter_values, 'view_type': 'list'},
        ])
        Step.create({**values, 'chapter_id': kanban_chapter.id, 'type': 'field', 'name': 'email'})
        Step.create({**values, 'chapter_id': kanban_chapter.id, 'type': 'generic_button', 'name': 'Edit'})
        with self.assertRaises(ValidationError):
            Step.create({**values, 'chapter_id': list_chapter.id, 'type': 'field', 'name': 'email'})
        with self.assertRaises(ValidationError):
            kanban_chapter.view_type = 'list'
        with self.assertRaises(ValidationError):
            list_chapter.context = "[1, 2]"
