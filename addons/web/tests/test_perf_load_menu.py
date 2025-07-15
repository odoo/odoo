
import json
from uuid import uuid4

from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestPerfSessionInfo(common.HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Improve stability of query count by using dedicated company and user.
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company',
        })
        cls.user = common.new_test_user(
            cls.env,
            "session",
            email="session@in.fo",
            tz="UTC",
            company_id=cls.company.id,
        )

    def setUp(self):
        super().setUp()
        self.uid = self.user

    def test_performance_session_info(self):
        self.authenticate(self.user.login, "info")

        self.env.registry.clear_all_caches()
        # cold ormcache:
        # - Only web: 43
        # - All modules: 121
        with self.assertQueryCount(121):
            self.url_open(
                "/web/session/get_session_info",
                data=json.dumps({'jsonrpc': "2.0", 'method': "call", 'id': str(uuid4())}),
                headers={"Content-Type": "application/json"},
            )

        # cold fields cache - warm ormcache:
        # - Only web: 5
        # - All modules: 32
        with self.assertQueryCount(32):
            self.url_open(
                "/web/session/get_session_info",
                data=json.dumps({'jsonrpc': "2.0", 'method': "call", 'id': str(uuid4())}),
                headers={"Content-Type": "application/json"},
            )

    def test_load_web_menus_perf(self):
        self.env.registry.clear_all_caches()
        self.env.invalidate_all()
        # cold orm/fields cache:
        # - Web only: 14
        # - All modules 57
        with self.assertQueryCount(57):
            self.env['ir.ui.menu'].load_web_menus(False)

        # cold fields cache:
        # - Web only: 0
        # - All modules: 1 (web_studio + 1)
        self.env.invalidate_all()
        with self.assertQueryCount(1):
            self.env['ir.ui.menu'].load_web_menus(False)

    def test_load_menus_perf(self):
        self.env.registry.clear_all_caches()
        self.env.invalidate_all()
        # cold orm/fields cache:
        # - Web only: 14
        # - All modules 57
        with self.assertQueryCount(57):
            self.env['ir.ui.menu'].load_menus(False)

        # cold fields cache:
        # - Web only: 0
        # - All modules: 1 (web_studio + 1)
        self.env.invalidate_all()
        with self.assertQueryCount(1):
            self.env['ir.ui.menu'].load_menus(False)

    def test_visible_menu_ids(self):
        self.env.registry.clear_all_caches()
        self.env.invalidate_all()
        # cold ormcache:
        # - Only web 13
        # - All modules: 21
        with self.assertQueryCount(21):
            self.env['ir.ui.menu']._visible_menu_ids()

        # cold fields cache - warm orm cache (only web: 0, all module: 0)
        self.env.invalidate_all()
        with self.assertQueryCount(0):
            self.env['ir.ui.menu']._visible_menu_ids()
