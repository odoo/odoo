from unittest.mock import patch

from freezegun import freeze_time
from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
from odoo.modules import module
from odoo.tests import Form, TransactionCase, new_test_user
from odoo.tools import mute_logger


class TestWebTutorial(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login='tuto_user', groups='base.group_user,base.group_partner_manager')
        cls.env['ir.config_parameter'].sudo().set_str('database.expiration_reason', 'trial')
        cls.partner_action = cls.env['ir.actions.act_window'].create({
            'name': 'Tuto Partners', 'res_model': 'res.partner', 'path': 'tuto-partners', 'view_mode': 'list,kanban,form',
        })
        cls.tutorial = cls.env['web_tutorial.tutorial'].create({'title': 'test_tutorial'})
        cls.form_values = {'tutorial_id': cls.tutorial.id, 'action_id': cls.partner_action.id}
        cls.email_step, cls.phone_step = cls.env['web_tutorial.step'].create([
            {**cls.form_values, 'type': 'field', 'name': 'email', 'message': "Fill in the email"},
            {**cls.form_values, 'type': 'field', 'name': 'phone', 'message': "Fill in the phone"},
        ])

    def create_tutorial(self, title, action=None, **values):
        """ Return a tutorial starting from the action (the one of the
        partners, by default) with the New button of its list """
        return self.env['web_tutorial.tutorial'].create({
            'title': title,
            **values,
            'step_ids': [Command.create({
                'action_id': (action or self.partner_action).id, 'type': 'generic_button', 'name': 'New',
                'message': "Create one",
            })],
        })

    def get_running_tutorials(self, user=None):
        """ Return the running tutorials created by these tests """
        with patch.object(module, 'current_test', None):
            tutorials = self.env['web_tutorial.tutorial'].with_user(user or self.user).get_running_tutorials()
        return [tutorial for tutorial in tutorials if tutorial['title'] in ('test_tutorial', 'cron_tutorial')]

    def test_only_started_tutorials_run_outside_trial(self):
        self.env['ir.config_parameter'].sudo().set_str('database.expiration_reason', 'renewal')
        self.assertEqual(self.get_running_tutorials(), [])
        tutorial = self.tutorial.with_user(self.user)
        tutorial.action_restart()
        self.assertEqual([tutorial['title'] for tutorial in self.get_running_tutorials()], ['test_tutorial'])
        tutorial.mark_done()
        self.assertEqual(self.get_running_tutorials(), [])
        tutorial.action_restart()
        self.tutorial.active = False
        self.assertEqual(self.get_running_tutorials(), [])

    def test_invalid_steps_ignored(self):
        other_tutorial = self.env['web_tutorial.tutorial'].create({'title': 'other_tutorial'})
        other_step = self.env['web_tutorial.step'].create({
            **self.form_values,
            'tutorial_id': other_tutorial.id,
            'type': 'field',
            'name': 'name',
            'message': "Name it",
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
        second_tutorial = self.create_tutorial('second_tutorial', sequence=2)
        first_tutorial = self.create_tutorial('first_tutorial', sequence=1)
        self.env['ir.model.data'].create([
            {'module': 'tuto_module', 'name': tutorial.title, 'model': tutorial._name, 'res_id': tutorial.id}
            for tutorial in second_tutorial + first_tutorial
        ])

        def get_running_names():
            with patch.object(module, 'current_test', None):
                tutorials = self.env['web_tutorial.tutorial'].with_user(self.user).get_running_tutorials()
            return [tutorial['title'] for tutorial in tutorials if tutorial['title'] in ('first_tutorial', 'second_tutorial')]

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
        self.tutorial.key = 'test_tutorial'
        self.assertFalse(tutorial.start_from_key('test_tutorial'))
        self.assertFalse(self.env['web_tutorial.progress'].search([('user_id', '=', portal.id)]))

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
        self.assertFalse(self.env['web_tutorial.progress'].with_user(other_user).search([]))
        with self.assertRaises(AccessError):
            progress.with_user(other_user).read(['done'])
        with self.assertRaises(AccessError):
            progress.with_user(other_user).write({'done': False})
        with self.assertRaises(AccessError):
            self.env['web_tutorial.progress'].with_user(other_user).create({
                'tutorial_id': self.create_tutorial('other_tutorial').id, 'user_id': self.user.id,
            })

    def test_restart(self):
        tutorial = self.tutorial.with_user(self.user)
        tutorial.mark_steps_done(self.email_step.ids)
        tutorial.mark_done()
        self.assertEqual(self.get_running_tutorials(), [])

        with patch.object(module, 'current_test', None):
            action = tutorial.action_restart()
        self.assertEqual(action['tag'], 'web_tutorial.start')
        self.assertEqual(action['params']['action_id'], self.partner_action.id)
        self.assertEqual(
            [running['title'] for running in action['params']['running_tutorials'] if running['title'] == 'test_tutorial'],
            ['test_tutorial'],
        )
        self.assertFalse(tutorial._get_user_progress().done_step_ids)
        self.assertEqual(len(self.get_running_tutorials()), 1)

    def test_start_from_key(self):
        self.env['ir.config_parameter'].sudo().set_str('database.expiration_reason', 'renewal')
        Tutorial = self.env['web_tutorial.tutorial'].with_user(self.user)
        tutorial = self.tutorial.with_user(self.user)
        self.tutorial.key = 'test_tutorial'
        self.assertFalse(Tutorial.start_from_key('no_such_tutorial'))
        self.assertFalse(Tutorial.start_from_key(''))
        self.assertEqual(self.get_running_tutorials(), [])

        action = Tutorial.start_from_key('test_tutorial')
        self.assertEqual(action['params']['action_id'], self.partner_action.id)
        self.assertEqual([tutorial['title'] for tutorial in self.get_running_tutorials()], ['test_tutorial'])
        tutorial.mark_steps_done(self.email_step.ids)
        Tutorial.start_from_key('test_tutorial')
        self.assertEqual(tutorial._get_user_progress().done_step_ids, self.email_step)

        tutorial.mark_done()
        Tutorial.start_from_key('test_tutorial')
        self.assertFalse(tutorial._get_user_progress().done_step_ids)
        self.assertEqual(len(self.get_running_tutorials()), 1)

        Tutorial.start_from_key('test_tutorial', True)
        tutorial_data = self.get_running_tutorials()[0]
        self.assertEqual((tutorial_data['expand_messages'], tutorial_data['user_expand_messages']), (False, True))
        admin = self.env.ref('base.user_admin')
        Tutorial.with_user(admin).start_from_key('test_tutorial')
        self.assertFalse(self.get_running_tutorials(admin)[0]['user_expand_messages'])
        Tutorial.start_from_key('test_tutorial')
        self.assertFalse(self.get_running_tutorials()[0]['user_expand_messages'])

        self.partner_action.group_ids = self.env.ref('base.group_system')
        self.assertFalse(Tutorial.start_from_key('test_tutorial'))

    def test_key(self):
        Tutorial = self.env['web_tutorial.tutorial']
        tutorial = Tutorial._load_records([{'xml_id': 'web_tutorial.data_tutorial', 'values': {'title': "Data"}}])
        self.assertEqual(tutorial.key, 'web_tutorial.data_tutorial')
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError):
            Tutorial.create({'title': "Copy", 'key': 'web_tutorial.data_tutorial'})

    def test_running_tutorials_access(self):
        cron_action = self.env['ir.actions.act_window'].create({'name': 'Tuto Crons', 'res_model': 'ir.cron'})
        cron_tutorial = self.create_tutorial('cron_tutorial', action=cron_action)
        admin = self.env.ref('base.user_admin')
        self.assertEqual([tutorial['title'] for tutorial in self.get_running_tutorials()], ['test_tutorial'])
        cron_tutorial.with_user(self.user).mark_done()
        self.assertFalse(cron_tutorial.with_user(self.user)._get_user_progress())
        self.assertEqual(
            [tutorial['title'] for tutorial in self.get_running_tutorials(admin)],
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
        self.assertEqual([tutorial['title'] for tutorial in self.get_running_tutorials()], ['test_tutorial'])

        self.partner_action.group_ids = self.env.ref('base.group_system')
        self.assertEqual(self.get_running_tutorials(), [])
        self.assertIn('test_tutorial', [tutorial['title'] for tutorial in self.get_running_tutorials(admin)])

    def test_running_tutorial_steps(self):
        self.assertFalse(self.get_running_tutorials()[0]['expand_messages'])
        self.tutorial.expand_messages = True
        self.assertTrue(self.get_running_tutorials()[0]['expand_messages'])
        action = self.create_server_action()
        delete_step, action_step, menu_step = self.env['web_tutorial.step'].create([
            {
                **self.form_values, 'type': 'generic_button', 'name': 'Delete', 'message': "Delete it",
                'skippable': True,
            },
            {**self.form_values, 'type': 'server_action', 'name': 'web_tutorial.test_action', 'message': "Run it"},
            {**self.form_values, 'type': 'menu_item', 'name': 'base.menu_action_res_users', 'message': "Open it"},
        ])
        step_data = {
            'action_id': self.partner_action.id, 'action_name': "", 'menu_section': "",
            'res_model': 'res.partner', 'skippable': False, 'view_types': [],
        }
        self.assertEqual(self.get_running_tutorials()[0]['steps'], [
            {**step_data, 'message': "<p>Fill in the email</p>", 'id': self.email_step.id, 'name': 'email', 'type': 'field'},
            {**step_data, 'message': "<p>Fill in the phone</p>", 'id': self.phone_step.id, 'name': 'phone', 'type': 'field'},
            {
                **step_data, 'message': "<p>Delete it</p>", 'skippable': True, 'id': delete_step.id, 'name': 'Delete',
                'type': 'generic_button',
            },
            {
                **step_data, 'action_name': action.name, 'message': "<p>Run it</p>", 'id': action_step.id,
                'name': 'web_tutorial.test_action', 'type': 'server_action',
            },
            {
                **step_data, 'menu_section': 'base.menu_users', 'message': "<p>Open it</p>", 'id': menu_step.id,
                'name': 'base.menu_action_res_users', 'type': 'menu_item',
            },
        ])
        menu = self.env['ir.ui.menu'].create({
            'name': "Tuto Partners", 'parent_id': self.env.ref('base.menu_users').id,
            'action': f'ir.actions.act_window,{self.partner_action.id}',
        })
        self.env['ir.model.data'].create({'module': 'web_tutorial', 'name': 'tuto_menu', 'model': menu._name, 'res_id': menu.id})
        menu_step.name = 'web_tutorial.tuto_menu'
        menu.unlink()
        self.assertEqual(self.get_running_tutorials()[0]['steps'][-1]['menu_section'], "")

    def test_step_views(self):
        Step = self.env['web_tutorial.step']
        values = {'tutorial_id': self.tutorial.id, 'type': 'field', 'name': 'email', 'message': "Do it"}
        self.assertEqual(self.email_step.model_id.model, 'res.partner')
        list_step = Step.create({**self.form_values, **values, 'view_types': 'list,kanban'})
        model_step = Step.create({**values, 'model_id': self.env['ir.model']._get_id('res.users')})
        self.assertEqual(
            [step['view_types'] for step in self.get_running_tutorials()[0]['steps']],
            [[], [], ['list', 'kanban'], []],
        )
        self.assertEqual(
            [(step['action_id'], step['res_model']) for step in self.get_running_tutorials()[0]['steps']][2:],
            [(self.partner_action.id, 'res.partner'), (False, 'res.users')],
        )
        model_step.action_id = self.partner_action
        self.assertEqual(model_step.res_model, 'res.partner')
        model_step.action_id = False
        model_step.model_id = self.env['ir.model']._get('res.users')
        self.assertEqual(self.tutorial.step_ids.mapped('chapter'), [1, 1, 2, 3])
        model_step.write({'model_id': self.env['ir.model']._get_id('res.partner'), 'view_types': 'list, kanban'})
        self.assertEqual(self.tutorial.step_ids.mapped('chapter'), [1, 1, 2, 2])
        model_step.action_id = self.env['ir.actions.act_window'].create({
            'name': 'Other', 'res_model': 'res.partner', 'view_mode': 'list,kanban',
        })
        self.assertEqual(self.tutorial.step_ids.mapped('chapter'), [1, 1, 2, 3])
        model_step.write({
            'action_id': False, 'model_id': self.env['ir.model']._get_id('res.users'), 'view_types': False,
        })
        with self.assertRaises(ValidationError):
            list_step.view_types = 'list,no_such_view'
        with self.assertRaises(ValidationError):
            list_step.view_types = 'calendar'
        with self.assertRaises(ValidationError):
            Step.create({**self.form_values, **values, 'model_id': model_step.model_id.id})
        with self.assertRaises(ValidationError):
            Step.create({**values, 'model_id': self.env['ir.model']._get_id('res.users'), 'sequence': 1})
        with self.assertRaises(ValidationError):
            self.tutorial.step_ids = [Command.unlink(step.id) for step in (self.email_step, self.phone_step, list_step)]
        self.partner_action.unlink()
        self.assertEqual(self.tutorial.step_ids, model_step)
        self.assertFalse(self.tutorial._is_accessible())

    def test_copy(self):
        tutorial = self.tutorial.copy()
        self.assertEqual(tutorial.step_ids.mapped('name'), ['email', 'phone'])
        self.assertFalse(tutorial.key)

    def test_starting_action(self):
        self.assertEqual(self.tutorial._get_starting_action(), self.partner_action)
        tutorial = self.env['web_tutorial.tutorial'].create({'title': 'empty_tutorial'})
        self.assertFalse(tutorial.with_user(self.user)._is_accessible())
        with self.assertRaises(AccessError):
            tutorial.with_user(self.user).action_restart()

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

    def test_dialog_step(self):
        Step = self.env['web_tutorial.step']
        Step.create({**self.form_values, 'type': 'dialog', 'message': "<h3>Welcome aboard</h3>"})
        step_data = self.get_running_tutorials()[0]['steps'][-1]
        self.assertEqual((step_data['type'], step_data['name']), ('dialog', ''))
        self.assertIn('<h3>Welcome aboard</h3>', step_data['message'])
        for invalid in [{'type': 'dialog', 'name': 'email'}, {'type': 'field'}]:
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                Step.create({**self.form_values, 'message': "Do it", **invalid})

    def test_name_selection_options(self):
        partner_model_id = self.env['ir.model']._get_id('res.partner')

        def get_values(step_type):
            step = self.env['web_tutorial.step'].new({'type': step_type, 'model_id': partner_model_id})
            return [value for value, _label in step.name_selection_options]

        self.assertEqual(get_values('generic_button'), ['New', 'Edit', 'Delete', 'Duplicate', 'Archive', 'Unarchive'])
        self.create_server_action()
        self.create_server_action(model='res.users', name='users_action')
        self.assertIn('web_tutorial.test_action', get_values('server_action'))
        self.assertNotIn('web_tutorial.users_action', get_values('server_action'))
        self.assertIn('base.menu_action_res_users', get_values('menu_item'))
        self.assertNotIn('base.menu_administration', get_values('menu_item'))
        self.assertEqual(get_values('field'), [])
        self.assertEqual(get_values('method'), [])

    def test_view_type_selection_options(self):
        Step = self.env['web_tutorial.step']
        all_view_types = [view_type for view_type, _label in Step.new({}).view_type_selection_options]
        self.assertTrue({'list', 'kanban', 'form', 'graph'} <= set(all_view_types))
        step = Step.new({'action_id': self.partner_action.id})
        self.assertEqual(
            [view_type for view_type, _label in step.view_type_selection_options],
            [view_type for view_type in all_view_types if view_type in ('list', 'kanban', 'form')],
        )

    def test_step_form(self):
        with Form(self.phone_step) as step:
            step.type = 'dialog'
        self.assertEqual((self.phone_step.name, self.phone_step.message), (False, "<p>Fill in the phone</p>"))
        with Form(self.phone_step) as step:
            step.type = 'field'
            step.name = 'phone'
            step.view_types = 'list,form'
            step.action_id = self.env['ir.actions.act_window'].create({
                'name': 'Partner Cards', 'res_model': 'res.partner', 'view_mode': 'kanban,form',
            })
            self.assertEqual(step.view_types, 'form')
            step.model_id = self.env['ir.model']._get('res.users')
            self.assertFalse(step.action_id)

    def test_step_names(self):
        Step = self.env['web_tutorial.step']
        values = {**self.form_values, 'message': "Do it"}
        self.create_server_action()
        self.create_server_action(model='res.users', name='other_model_action')
        self.create_server_action(name='unbound_action').binding_model_id = False
        Step.create({**values, 'type': 'field', 'name': 'child_ids.email'})
        Step.create({**values, 'type': 'method', 'name': 'write'})
        Step.create({**values, 'type': 'server_action', 'name': 'web_tutorial.test_action'})
        Step.create({**values, 'type': 'menu_item', 'name': 'base.menu_action_res_users'})
        for button in ('New', 'Edit', 'Delete', 'Duplicate', 'Archive', 'Unarchive'):
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
            {'type': 'menu_item', 'name': 'base.menu_administration'},
            {'type': 'menu_item', 'name': 'base.menu_users'},
            {'type': 'menu_item', 'name': 'web_tutorial.test_action'},
            {'type': 'generic_button', 'name': 'Save'},
        ]:
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                Step.create({**values, **invalid})
