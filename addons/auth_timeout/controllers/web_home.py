from odoo import http

from odoo.addons.web.controllers import home as web_home


class Home(web_home.Home):
    # `/web/webclient/load_menus` must be `check_identity=False`
    # because it is called in Javascript using a simple `fetch` rather than a `rpc(...)`
    # within a QWeb template (see `web.webclient_bootstrap` in `webclient_templates.xml`).
    # Only `rpc` is overriden to catch `CheckIdentityException` to display the screen lock dialog.
    # `fetch` isn't and therefore raises an error upon receiving a `CheckIdentityException`.
    @http.route(check_identity=False)
    def web_load_menus(self, lang=None):
        return super().web_load_menus(lang)
