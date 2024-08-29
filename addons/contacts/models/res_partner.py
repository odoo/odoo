# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base

from odoo import models


class ResPartner(models.Model, base.ResPartner):

    def _get_backend_root_menu_ids(self):
        return super()._get_backend_root_menu_ids() + [self.env.ref('contacts.menu_contacts').id]
