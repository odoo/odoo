from odoo.addons.web.controllers.home import Home


class HomePasswordPolicy(Home):

    def _prepare_value_change_password(self):
        # Note for me check _prepare_portal_layout_values how to add minlength
        pass