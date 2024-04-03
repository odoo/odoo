# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Partner(models.Model):
    _inherit = "res.partner"

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [self.env.ref('contacts.menu_contacts').id]
