from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests import tagged, HttpCase
from odoo.tools import mute_logger


@tagged('-at_install', 'post_install')
class TestShareLinkRefresh(TestProjectCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_pigs.privacy_visibility = 'portal'
        cls.project_pigs._portal_ensure_token()
        cls.task_1._portal_ensure_token()

    def _get_mail_view_url(self, model, res_id, access_token):
        return f'{self.base_url()}/mail/view?model={model}&res_id={res_id}&access_token={access_token}'

    @mute_logger('werkzeug')
    def test_valid_token(self):
        """A valid token should redirect to the portal record page (no access_error)."""
        for model, record in [
            ('project.project', self.project_pigs),
            ('project.task', self.task_1),
        ]:
            with self.subTest(model=model):
                url = self._get_mail_view_url(model, record.id, record.access_token)
                res = self.url_open(url)
                self.assertEqual(res.status_code, 200)
                self.assertNotIn('access_error', res.url)

    @mute_logger('werkzeug')
    def test_portal_user_old_token(self):
        """Portal user (non-collaborator) with an old token should be redirected to /my?access_error=1."""
        old_project_token = self.project_pigs.access_token
        old_task_token = self.task_1.access_token
        self.project_pigs.action_regenerate_access_token()
        self.task_1.action_regenerate_access_token()
        self.assertNotEqual(self.project_pigs.access_token, old_project_token)
        self.assertNotEqual(self.task_1.access_token, old_task_token)

        self.authenticate(self.user_portal.login, self.user_portal.login)
        for model, res_id, old_token in [
            ('project.project', self.project_pigs.id, old_project_token),
            ('project.task', self.task_1.id, old_task_token),
        ]:
            with self.subTest(model=model):
                url = self._get_mail_view_url(model, res_id, old_token)
                res = self.url_open(url)
                self.assertEqual(res.status_code, 200)
                self.assertURLEqual(res.url, f'{self.base_url()}/my?access_error=1')

    @mute_logger('werkzeug')
    def test_public_user_old_token(self):
        """Public (not logged in) user with an old token should be redirected to /web/login?access_error=1."""
        old_project_token = self.project_pigs.access_token
        old_task_token = self.task_1.access_token
        self.project_pigs.action_regenerate_access_token()
        self.task_1.action_regenerate_access_token()
        self.assertNotEqual(self.project_pigs.access_token, old_project_token)
        self.assertNotEqual(self.task_1.access_token, old_task_token)

        for model, res_id, old_token in [
            ('project.project', self.project_pigs.id, old_project_token),
            ('project.task', self.task_1.id, old_task_token),
        ]:
            with self.subTest(model=model):
                url = self._get_mail_view_url(model, res_id, old_token)
                res = self.url_open(url)
                self.assertEqual(res.status_code, 200)
                self.assertURLEqual(res.url, f'{self.base_url()}/web/login?access_error=1')
