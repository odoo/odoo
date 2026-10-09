from odoo import models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    def has_debug_group(self, *args, **kwargs):
        user = self.env.user
        if self.env.is_superuser():
            return True
        has_group = user.has_group('odx_restrict_debug.group_allow_debug')
        return has_group
