from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.modules import module
from odoo.tests import TransactionCase, new_test_user
from odoo.tools import mute_logger


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
        cls.chapter = cls.env['web_tuto.chapter'].create({'tutorial_id': cls.tutorial.id, 'view_id': cls.form_view.id})
        cls.email_step, cls.archive_step, cls.restore_step, cls.send_step = cls.env['web_tuto.step'].create([
            {'chapter_id': cls.chapter.id, 'type': 'field', 'name': 'email', 'content': 'Do it', 'sequence': 1},
            {'chapter_id': cls.chapter.id, 'type': 'button', 'name': 'action_archive', 'content': 'Do it', 'sequence': 2},
            {'chapter_id': cls.chapter.id, 'type': 'button', 'name': 'action_unarchive', 'content': 'Do it', 'sequence': 3},
            {'chapter_id': cls.chapter.id, 'type': 'button', 'name': 'send', 'content': 'Do it', 'sequence': 4},
        ])

    def get_running_tutorials(self, user=None):
        """ Return the running tutorials created by these tests """
        with patch.object(module, 'current_test', None):
            tutorials = self.env['web_tuto.tutorial'].with_user(user or self.user).get_running_tutorials()
        return [tutorial for tutorial in tutorials if tutorial['name'] in ('test_tutorial', 'cron_tutorial')]

    def test_resolve_steps(self):
        self.assertEqual(self.email_step.tutorial_id, self.tutorial)
        steps = self.get_running_tutorials()[0]['chapters'][0]['steps']
        self.assertEqual(
            [(step['type'], step['name'], step['content']) for step in steps],
            [
                ('field', 'email', 'Do it'), ('button', 'action_archive', 'Do it'),
                ('button', 'action_unarchive', 'Do it'), ('button', 'send', 'Do it'),
            ],
        )

    def test_resolve_line_fields(self):
        form_view = self.env['ir.ui.view'].create({
            'name': 'tuto.partner.children.form',
            'model': 'res.partner',
            'type': 'form',
            'arch': """
                <form>
                    <field name="child_ids">
                        <list editable="bottom">
                            <field name="email" string="Contact Mail"/>
                            <field name="phone"/>
                        </list>
                    </field>
                </form>""",
        })
        chapter = self.env['web_tuto.chapter'].create({'tutorial_id': self.tutorial.id, 'view_id': form_view.id})
        self.env['web_tuto.step'].create([
            {'chapter_id': chapter.id, 'type': 'field', 'name': 'child_ids', 'content': 'Do it', 'sequence': 1},
            {'chapter_id': chapter.id, 'type': 'field', 'name': 'child_ids.email', 'content': 'Do it', 'sequence': 2},
            {'chapter_id': chapter.id, 'type': 'field', 'name': 'child_ids.phone', 'content': 'Do it', 'sequence': 3},
        ])
        steps = self.get_running_tutorials()[0]['chapters'][1]['steps']
        self.assertEqual(
            [(step['name'], step.get('x2many')) for step in steps],
            [('child_ids', None), ('email', 'child_ids'), ('phone', 'child_ids')],
        )
        with self.assertRaises(ValidationError):
            self.env['web_tuto.step'].create({'chapter_id': chapter.id, 'type': 'field', 'name': 'child_ids.mobile', 'content': 'Do it'})
        with self.assertRaises(ValidationError):
            self.env['web_tuto.step'].create({'chapter_id': self.chapter.id, 'type': 'field', 'name': 'email.name', 'content': 'Do it'})

    def test_tooltip_position(self):
        self.archive_step.tooltip_position = 'right'
        steps = self.get_running_tutorials()[0]['chapters'][0]['steps']
        self.assertEqual(
            [step['tooltip_position'] for step in steps],
            ['bottom', 'right', 'bottom', 'bottom'],
        )

    def test_invalid_steps(self):
        Step = self.env['web_tuto.step']
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            Step.create({'chapter_id': self.chapter.id, 'type': 'field', 'name': 'email'})
        with self.assertRaises(ValidationError):
            Step.create({'chapter_id': self.chapter.id, 'type': 'button', 'name': 'unknown', 'content': 'Do it'})
        with self.assertRaises(ValidationError):
            Step.create({'chapter_id': self.chapter.id, 'type': 'button', 'name': 'create', 'content': 'Do it'})
        with self.assertRaises(ValidationError):
            Step.create({'chapter_id': self.chapter.id, 'type': 'field', 'name': 'action_archive', 'content': 'Do it'})
        with self.assertRaises(ValidationError):
            Step.create({'chapter_id': self.chapter.id, 'type': 'button', 'name': 'email', 'content': 'Do it'})

    def test_ambiguous_button(self):
        Step = self.env['web_tuto.step']
        generic_buttons = dict(Step._get_generic_buttons(), action_archive=('form',))
        with (
            patch.object(self.registry['web_tuto.step'], '_get_generic_buttons', lambda self: generic_buttons),
            self.assertRaisesRegex(ValidationError, "both a button of the view .* and a generic button"),
        ):
            Step.create({'chapter_id': self.chapter.id, 'type': 'button', 'name': 'action_archive', 'content': 'Do it'})

    def test_progress(self):
        self.email_step.with_user(self.user).mark_done()
        steps = self.get_running_tutorials()[0]['chapters'][0]['steps']
        self.assertEqual([step['done'] for step in steps], [True, False, False, False])

        self.email_step.with_user(self.user).mark_undone()
        steps = self.get_running_tutorials()[0]['chapters'][0]['steps']
        self.assertEqual([step['done'] for step in steps], [False, False, False, False])

        self.tutorial.with_user(self.user).mark_done()
        self.assertEqual(self.get_running_tutorials(), [])

    def test_restart(self):
        admin = self.env.ref('base.user_admin')
        self.archive_step.with_user(admin).mark_done()
        self.tutorial.with_user(admin).mark_done()
        self.assertEqual(self.get_running_tutorials(admin), [])

        action = self.tutorial.with_user(admin).action_restart()
        self.assertEqual(action['tag'], 'reload')
        self.assertTrue(action['params']['action_id'])
        self.assertFalse(self.archive_step.user_done_ids)
        self.assertTrue(admin.tutorial_enabled)
        self.assertEqual(len(self.get_running_tutorials(admin)), 1)

    def test_user_tutorials(self):
        self.tutorial.title = 'Test Tutorial'

        def get_user_tutorial():
            tutorials = self.env['web_tuto.tutorial'].with_user(self.user).get_user_tutorials()
            return next(
                (tutorial['title'], tutorial['state'], tutorial['chapters'])
                for tutorial in tutorials if tutorial['id'] == self.tutorial.id
            )

        self.assertEqual(get_user_tutorial(), ('Test Tutorial', 'new', [[False, False, False, False]]))
        self.archive_step.with_user(self.user).mark_done()
        self.assertEqual(get_user_tutorial(), ('Test Tutorial', 'running', [[True, True, False, False]]))
        self.tutorial.with_user(self.user).mark_done()
        self.assertEqual(get_user_tutorial(), ('Test Tutorial', 'done', [[True, True, True, True]]))
        self.tutorial.sudo().user_done_ids = False
        (self.email_step | self.restore_step | self.send_step).with_user(self.user).mark_done()
        self.assertEqual(get_user_tutorial(), ('Test Tutorial', 'running', [[True, True, True, True]]))

        self.env['ir.model.data'].create({
            'module': 'web_tuto', 'name': 'test_tutorial', 'model': self.tutorial._name, 'res_id': self.tutorial.id,
        })
        self.assertEqual(get_user_tutorial()[0], 'Tutorials - Test Tutorial')

    def test_resume(self):
        self.user.tutorial_enabled = False
        self.email_step.with_user(self.user).mark_done()
        action = self.tutorial.with_user(self.user).action_resume()
        self.assertEqual(action['tag'], 'reload')
        self.assertTrue(self.user.tutorial_enabled)
        self.assertIn(self.user, self.email_step.user_done_ids)

    def test_resume_url(self):
        partner = self.env['res.partner'].create({'name': 'Tuto Partner'})
        child = self.env['res.partner'].create({'name': 'Tuto Child', 'parent_id': partner.id})
        self.env['ir.actions.act_window'].create({
            'name': 'Tuto Partners', 'res_model': 'res.partner', 'path': 'tuto-partners',
        })
        tutorial = self.tutorial.with_user(self.user)
        url = f'/odoo/tuto-partners/{partner.id}/m-res.partner/{child.id}?debug=1'
        tutorial.save_resume_url(url)
        self.assertEqual(tutorial.action_resume(), {'type': 'ir.actions.act_url', 'url': url, 'target': 'self'})

        tutorial.save_resume_url('//evil.com/odoo')
        self.assertEqual(tutorial.action_resume()['url'], url)

        child.unlink()
        self.assertEqual(tutorial.action_resume()['url'], f'/odoo/tuto-partners/{partner.id}/m-res.partner/new')
        tutorial.save_resume_url(f'/odoo/tuto-partners/{partner.id}/m-res.partner')
        partner.unlink()
        self.assertEqual(tutorial.action_resume()['url'], '/odoo/tuto-partners')

        tutorial.save_resume_url('/odoo/tuto-partners/new')
        self.assertEqual(tutorial.action_resume()['url'], '/odoo/tuto-partners/new')
        tutorial.save_resume_url('/odoo/no-such-action/1')
        self.assertEqual(tutorial.action_resume()['tag'], 'reload')
        tutorial.save_resume_url('/odoo/tuto-partners')
        self.assertEqual(tutorial.action_restart()['tag'], 'reload')
        self.assertEqual(tutorial.action_resume()['tag'], 'reload')

    def test_running_tutorials_access(self):
        cron_view = self.env['ir.ui.view'].create({
            'name': 'tuto.cron.form',
            'model': 'ir.cron',
            'type': 'form',
            'arch': '<form><field name="cron_name"/></form>',
        })
        cron_tutorial = self.env['web_tuto.tutorial'].create({'name': 'cron_tutorial'})
        cron_chapter = self.env['web_tuto.chapter'].create({'tutorial_id': cron_tutorial.id, 'view_id': cron_view.id})
        self.env['web_tuto.step'].create({'chapter_id': cron_chapter.id, 'type': 'field', 'name': 'cron_name', 'content': 'Do it'})
        self.assertEqual([tutorial['name'] for tutorial in self.get_running_tutorials()], ['test_tutorial'])
        admin = self.env.ref('base.user_admin')
        admin.tutorial_enabled = True
        self.assertEqual(
            [tutorial['name'] for tutorial in self.get_running_tutorials(admin)],
            ['cron_tutorial', 'test_tutorial'],
        )

    def test_one_running_tutorial_by_module(self):
        second_tutorial, first_tutorial = self.env['web_tuto.tutorial'].create([
            {'name': 'second_tutorial', 'sequence': 2},
            {'name': 'first_tutorial', 'sequence': 1},
        ])
        for tutorial in second_tutorial + first_tutorial:
            self.env['web_tuto.chapter'].create({'tutorial_id': tutorial.id, 'view_id': self.form_view.id})
        self.env['ir.model.data'].create([
            {'module': 'tuto_module', 'name': tutorial.name, 'model': tutorial._name, 'res_id': tutorial.id}
            for tutorial in second_tutorial + first_tutorial
        ])

        def get_running_names():
            with patch.object(module, 'current_test', None):
                tutorials = self.env['web_tuto.tutorial'].with_user(self.user).get_running_tutorials()
            return [tutorial['name'] for tutorial in tutorials if tutorial['name'] in ('first_tutorial', 'second_tutorial')]

        self.assertEqual(get_running_names(), ['first_tutorial'])
        first_tutorial.with_user(self.user).mark_done()
        self.assertEqual(get_running_names(), ['second_tutorial'])

    def test_no_tutorial_during_tests(self):
        Tutorial = self.env['web_tuto.tutorial'].with_user(self.user)
        self.assertFalse(Tutorial.has_running_tutorials())
        self.assertEqual(Tutorial.get_running_tutorials(), [])
        with patch.object(module, 'current_test', None):
            self.assertTrue(Tutorial.has_running_tutorials())

    def test_enabled_in_trial(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_str('database.expiration_reason', 'renewal')
        user = new_test_user(self.env, login='trial_user', groups='base.group_user')
        self.assertFalse(user.tutorial_enabled)
        ICP.set_str('database.expiration_reason', 'trial')
        user.invalidate_recordset(['tutorial_enabled'])
        self.assertTrue(user.tutorial_enabled)
        user.with_user(user).write({'tutorial_enabled': False})
        user.invalidate_recordset(['tutorial_enabled'])
        self.assertFalse(user.tutorial_enabled)

    def test_user_switches_tutorials(self):
        self.user.with_user(self.user).write({'tutorial_enabled': False})
        self.assertFalse(self.user.tutorial_enabled)
        self.user.with_user(self.user).write({'tutorial_tips_shown': True})
        self.assertTrue(self.user.tutorial_tips_shown)

    def test_disabled_tutorials(self):
        self.user.tutorial_enabled = False
        self.assertEqual(self.get_running_tutorials(), [])
