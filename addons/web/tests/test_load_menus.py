from odoo.tests.common import HttpCase

class LoadMenusTests(HttpCase):

    def setUp(self):
        super().setUp()
        self.menu = self.env["ir.ui.menu"].create({
            "name": "test_menu",
            "parent_id": False,
        })

        def search(*args, **kwargs):
            return self.menu

        self.patch(type(self.env["ir.ui.menu"]), "search", search)
        self.authenticate("admin", "admin")

    def test_load_menus(self):
        menu_loaded = self.url_open("/web/webclient/load_menus/1234")
        expected = {
            str(self.menu.id): {
                "actionID": False,
                "actionModel": False,
                "actionPath": False,
                "appID": self.menu.id,
                "children": [],
                "id": self.menu.id,
                "name": "test_menu",
                "webIcon": False,
                "webIconData": "/web/static/img/default_icon_app.png",
                "webIconDataMimetype": False,
                "xmlid": ""
            },
            "root": {
                "actionID": False,
                "actionModel": False,
                "actionPath": False,
                "appID": False,
                "children": [
                    self.menu.id,
                ],
                "id": "root",
                "name": "root",
                "webIcon": None,
                "webIconData": None,
                "webIconDataMimetype": None,
                "xmlid": "",
                "backgroundImage": None,
            }
        }

        self.assertDictEqual(
            menu_loaded.json(),
            expected,
            "load_menus didn't return the expected value"
        )
