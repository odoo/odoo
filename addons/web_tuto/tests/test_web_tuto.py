from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.modules import module
from odoo.tests import TransactionCase, new_test_user


class TestWebTuto(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login='tuto_user', groups='base.group_user,base.group_partner_manager')
        cls.user.tutorial_enabled = True
        cls.form_view = cls.env['ir.ui.view'].create({
            'name': 'tuto.partner.form',
            'model': 'res.partner',
            'type': 'form',
            'arch': """
                <form>
                    <header>
                        <button name="action_archive" type="object" string="Archive"/>
                        <button name="action_unarchive" type="object">Restore</button>
                    </header>
                    <field name="name"/>
                    <field name="email" string="Mail"/>
                </form>""",
        })
        cls.tutorial = cls.env['web_tuto.tutorial'].create({'name': 'test_tutorial'})
        cls.view_step = cls.env['web_tuto.step'].create({'tutorial_id': cls.tutorial.id, 'view_id': cls.form_view.id})
        cls.email_step, cls.archive_step, cls.restore_step, cls.send_step = cls.env['web_tuto.step'].create([
            {'parent_id': cls.view_step.id, 'action': 'email', 'sequence': 1},
            {'parent_id': cls.view_step.id, 'action': 'action_archive', 'sequence': 2},
            {'parent_id': cls.view_step.id, 'action': 'action_unarchive', 'sequence': 3},
            {'parent_id': cls.view_step.id, 'action': 'send', 'sequence': 4},
        ])

    def get_running_tutorials(self, user=None):
        """ Return the running tutorials created by these tests """
        with patch.object(module, 'current_test', None):
            tutorials = self.env['web_tuto.tutorial'].with_user(user or self.user).get_running_tutorials()
        return [tutorial for tutorial in tutorials if tutorial['name'] in ('test_tutorial', 'cron_tutorial')]

    def test_resolve_actions(self):
        self.assertEqual(self.email_step.tutorial_id, self.tutorial)
        actions = self.get_running_tutorials()[0]['views'][0]['actions']
        self.assertEqual(
            [(action['kind'], action.get('name') or action.get('verb'), action['label']) for action in actions],
            [
                ('field', 'email', 'Mail'), ('button', 'action_archive', 'Archive'),
                ('button', 'action_unarchive', 'Restore'), ('verb', 'send', ''),
            ],
        )

    def test_invalid_steps(self):
        Step = self.env['web_tuto.step']
        with self.assertRaises(ValidationError):
            Step.create({'parent_id': self.view_step.id, 'action': 'unknown'})
        with self.assertRaises(ValidationError):
            Step.create({'parent_id': self.view_step.id, 'action': 'add_stage'})
        with self.assertRaises(ValidationError):
            Step.create({'tutorial_id': self.tutorial.id, 'view_id': self.form_view.id, 'action': 'email'})
        with self.assertRaises(ValidationError):
            Step.create({'parent_id': self.email_step.id, 'action': 'email'})

    def test_progress(self):
        self.email_step.with_user(self.user).mark_done()
        actions = self.get_running_tutorials()[0]['views'][0]['actions']
        self.assertEqual([action['done'] for action in actions], [True, False, False, False])

        self.email_step.with_user(self.user).mark_undone()
        actions = self.get_running_tutorials()[0]['views'][0]['actions']
        self.assertEqual([action['done'] for action in actions], [False, False, False, False])

        self.tutorial.with_user(self.user).consume()
        self.assertEqual(self.get_running_tutorials(), [])

    def test_restart(self):
        admin = self.env.ref('base.user_admin')
        self.archive_step.with_user(admin).mark_done()
        self.tutorial.with_user(admin).consume()
        self.assertEqual(self.get_running_tutorials(admin), [])

        action = self.tutorial.with_user(admin).action_restart()
        self.assertEqual(action['tag'], 'reload')
        self.assertTrue(action['params']['action_id'])
        self.assertFalse(self.archive_step.user_done_ids)
        self.assertTrue(admin.tutorial_enabled)
        self.assertEqual(len(self.get_running_tutorials(admin)), 1)

    def test_running_tutorials_access(self):
        cron_view = self.env['ir.ui.view'].create({
            'name': 'tuto.cron.form',
            'model': 'ir.cron',
            'type': 'form',
            'arch': '<form><field name="cron_name"/></form>',
        })
        cron_tutorial = self.env['web_tuto.tutorial'].create({'name': 'cron_tutorial'})
        cron_view_step = self.env['web_tuto.step'].create({'tutorial_id': cron_tutorial.id, 'view_id': cron_view.id})
        self.env['web_tuto.step'].create({'parent_id': cron_view_step.id, 'action': 'cron_name'})
        self.assertEqual([tutorial['name'] for tutorial in self.get_running_tutorials()], ['test_tutorial'])
        admin = self.env.ref('base.user_admin')
        admin.tutorial_enabled = True
        self.assertEqual(
            [tutorial['name'] for tutorial in self.get_running_tutorials(admin)],
            ['cron_tutorial', 'test_tutorial'],
        )

    def test_no_tutorial_during_tests(self):
        Tutorial = self.env['web_tuto.tutorial'].with_user(self.user)
        self.assertFalse(Tutorial.has_running_tutorials())
        self.assertEqual(Tutorial.get_running_tutorials(), [])
        with patch.object(module, 'current_test', None):
            self.assertTrue(Tutorial.has_running_tutorials())

    def test_disabled_tutorials(self):
        self.user.tutorial_enabled = False
        self.assertEqual(self.get_running_tutorials(), [])
