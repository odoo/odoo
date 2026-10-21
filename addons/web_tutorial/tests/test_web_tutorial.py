from unittest.mock import patch

from freezegun import freeze_time

from odoo.exceptions import AccessError
from odoo.modules import module
from odoo.tests import TransactionCase, new_test_user


class TestWebTutorial(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login='tuto_user', groups='base.group_user,base.group_partner_manager')
        cls.user.tutorial_enabled = True
        cls.partner_action = cls.env['ir.actions.act_window'].create({
            'name': 'Tuto Partners', 'res_model': 'res.partner', 'path': 'tuto-partners',
        })
        cls.tutorial = cls.env['web_tutorial.tutorial'].create({'action_id': cls.partner_action.id, 'name': 'test_tutorial'})

    def get_running_tutorials(self, user=None):
        """ Return the running tutorials created by these tests """
        with patch.object(module, 'current_test', None):
            tutorials = self.env['web_tutorial.tutorial'].with_user(user or self.user).get_running_tutorials()
        return [tutorial for tutorial in tutorials if tutorial['name'] in ('test_tutorial', 'cron_tutorial')]

    def get_user_tutorial_ids(self, user=None):
        """ Return the ids of the tutorials listed for the user """
        return [tutorial['id'] for tutorial in self.env['web_tutorial.tutorial'].with_user(user or self.user).get_user_tutorials()]

    def test_disabled_tutorials(self):
        self.user.tutorial_enabled = False
        self.assertEqual(self.get_running_tutorials(), [])

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

    def test_invalid_step_keys_ignored(self):
        tutorial = self.tutorial.with_user(self.user)
        tutorial.mark_steps_done('res.partner,form,email')
        tutorial.mark_steps_done([1])
        tutorial.mark_steps_done(['x' * 513])
        tutorial.mark_steps_done([f'res.partner,form,{index}' for index in range(1001)])
        self.assertFalse(tutorial._get_user_progress().done_steps)
        tutorial.save_resume_url('/odoo/' + 'x' * 2048)
        self.assertFalse(tutorial._get_user_progress().resume_url)

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
            first_tutorial.with_user(self.user).action_resume()
        self.assertEqual(get_running_names(), ['first_tutorial'])
        first_tutorial.with_user(self.user).mark_done()
        self.assertEqual(get_running_names(), ['second_tutorial'])

    def test_portal_user_has_no_progress(self):
        portal = new_test_user(self.env, login='tuto_portal', groups='base.group_portal')
        tutorial = self.tutorial.with_user(portal)
        tutorial.mark_done()
        tutorial.save_resume_url('/odoo/contacts')
        tutorial.mark_steps_done(['res.partner,form,email'])
        tutorial.mark_steps_undone(['res.partner,form,email'])
        self.assertFalse(self.env['web_tutorial.tutorial.user'].search([('user_id', '=', portal.id)]))
        self.assertEqual(tutorial.get_user_tutorials(), [])

    def test_progress(self):
        tutorial = self.tutorial.with_user(self.user)
        tutorial.mark_steps_done(['res.partner,form,email', 'res.partner,form,phone'])
        tutorial.mark_steps_done(['res.partner,form,email'])
        self.assertEqual(self.get_running_tutorials()[0]['done_steps'], ['res.partner,form,email', 'res.partner,form,phone'])

        tutorial.mark_steps_undone(['res.partner,form,email'])
        self.assertEqual(self.get_running_tutorials()[0]['done_steps'], ['res.partner,form,phone'])

        tutorial.mark_done()
        self.assertEqual(self.get_running_tutorials(), [])

    def test_progress_is_private(self):
        tutorial = self.tutorial.with_user(self.user)
        tutorial.mark_steps_done(['res.partner,form,email'])
        tutorial.mark_done()
        self.assertEqual(self.tutorial.write_uid, self.env.user)
        progress = tutorial._get_user_progress()
        self.assertTrue(progress.done)
        self.assertEqual(progress.done_steps, ['res.partner,form,email'])
        other_user = new_test_user(self.env, login='other_tuto_user', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.env['web_tutorial.tutorial.user'].with_user(other_user).search([])

    def test_resume_and_restart(self):
        self.user.tutorial_enabled = False
        tutorial = self.tutorial.with_user(self.user)
        tutorial.mark_steps_done(['res.partner,form,email'])
        action = tutorial.action_resume()
        self.assertEqual(action['tag'], 'reload')
        self.assertEqual(action['params']['action_id'], self.partner_action.id)
        self.assertTrue(self.user.tutorial_enabled)
        self.assertEqual(tutorial._get_user_progress().done_steps, ['res.partner,form,email'])

        tutorial.mark_done()
        self.assertEqual(self.get_running_tutorials(), [])
        self.assertEqual(tutorial.action_restart(), action)
        self.assertFalse(tutorial._get_user_progress().done_steps)
        self.assertEqual(len(self.get_running_tutorials()), 1)

    def test_resume_url(self):
        partner = self.env['res.partner'].create({'name': 'Tuto Partner'})
        child = self.env['res.partner'].create({'name': 'Tuto Child', 'parent_id': partner.id})
        tutorial = self.tutorial.with_user(self.user)
        url = f'/odoo/tuto-partners/{partner.id}/m-res.partner/{child.id}?debug=1'
        tutorial.save_resume_url(url)
        self.assertEqual(tutorial.action_resume(), {'type': 'ir.actions.act_url', 'url': url, 'target': 'self'})

        tutorial.save_resume_url('//evil.com/odoo')
        self.assertEqual(tutorial.action_resume()['url'], url)
        tutorial.save_resume_url('/\\evil.com/odoo')
        self.assertEqual(tutorial.action_resume()['url'], url)
        tutorial.save_resume_url('/\t/evil.com/odoo')
        self.assertEqual(tutorial.action_resume()['url'], url)
        tutorial.save_resume_url('/odoo.evil.com')
        self.assertEqual(tutorial.action_resume()['url'], url)

        child.unlink()
        self.assertEqual(tutorial.action_resume()['url'], f'/odoo/tuto-partners/{partner.id}/m-res.partner/new')
        tutorial.save_resume_url(f'/odoo/tuto-partners/{partner.id}/m-res.partner')
        partner.unlink()
        self.assertEqual(tutorial.action_resume()['url'], '/odoo/tuto-partners')

        hidden_partner = self.env['res.partner'].create({'name': 'Hidden Tuto Partner'})
        self.env['ir.access'].create({
            'name': 'Hide the partner of the tutorial',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'operation': 'r',
            'domain': f"[('id', '!=', {hidden_partner.id})]",
        })
        tutorial.save_resume_url(f'/odoo/tuto-partners/{hidden_partner.id}')
        self.assertEqual(tutorial.action_resume()['url'], '/odoo/tuto-partners/new')

        tutorial.save_resume_url('/odoo/tuto-partners/new')
        self.assertEqual(tutorial.action_resume()['url'], '/odoo/tuto-partners/new')
        tutorial.save_resume_url('/odoo/no-such-action/1')
        self.assertEqual(tutorial.action_resume()['tag'], 'reload')
        tutorial.save_resume_url('/odoo/tuto-partners')
        self.assertEqual(tutorial.action_restart()['tag'], 'reload')
        self.assertEqual(tutorial.action_resume()['tag'], 'reload')

    def test_running_tutorials_access(self):
        cron_action = self.env['ir.actions.act_window'].create({'name': 'Tuto Crons', 'res_model': 'ir.cron'})
        cron_tutorial = self.env['web_tutorial.tutorial'].create({'action_id': cron_action.id, 'name': 'cron_tutorial'})
        admin = self.env.ref('base.user_admin')
        admin.tutorial_enabled = True
        self.assertEqual([tutorial['name'] for tutorial in self.get_running_tutorials()], ['test_tutorial'])
        self.assertNotIn(cron_tutorial.id, self.get_user_tutorial_ids())
        cron_tutorial.with_user(self.user).mark_done()
        self.assertFalse(cron_tutorial.with_user(self.user)._get_user_progress())
        self.assertEqual(
            [tutorial['name'] for tutorial in self.get_running_tutorials(admin)],
            ['cron_tutorial', 'test_tutorial'],
        )

        self.partner_action.group_ids = self.env.ref('base.group_system')
        self.assertEqual(self.get_running_tutorials(), [])
        self.assertNotIn(self.tutorial.id, self.get_user_tutorial_ids())
        self.assertIn('test_tutorial', [tutorial['name'] for tutorial in self.get_running_tutorials(admin)])
        self.assertIn(self.tutorial.id, self.get_user_tutorial_ids(admin))

    def test_user_switches_tutorials(self):
        self.user.with_user(self.user).write({'tutorial_enabled': False})
        self.assertFalse(self.user.tutorial_enabled)
        self.user.with_user(self.user).write({'tutorial_tips_shown': True})
        self.assertTrue(self.user.tutorial_tips_shown)

    def test_user_tutorials(self):
        self.tutorial.title = 'Test Tutorial'
        tutorial = self.tutorial.with_user(self.user)

        def get_user_tutorial():
            tutorials = tutorial.get_user_tutorials()
            return next(
                (user_tutorial['title'], user_tutorial['state'], user_tutorial['done_steps'])
                for user_tutorial in tutorials if user_tutorial['id'] == self.tutorial.id
            )

        self.assertEqual(get_user_tutorial(), ('Test Tutorial', 'new', []))
        tutorial.mark_steps_done(['res.partner,form,email'])
        self.assertEqual(get_user_tutorial(), ('Test Tutorial', 'running', ['res.partner,form,email']))
        tutorial.mark_done()
        self.assertEqual(get_user_tutorial(), ('Test Tutorial', 'done', ['res.partner,form,email']))

        self.env['ir.model.data'].create({
            'module': 'web_tutorial', 'name': 'test_tutorial', 'model': self.tutorial._name, 'res_id': self.tutorial.id,
        })
        self.assertEqual(get_user_tutorial()[0], 'Tutorials - Test Tutorial')
