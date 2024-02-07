# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools


class Lang(models.Model):
    _inherit = "res.lang"

    @api.model
    @tools.ormcache()
    def get_available(self):
        """ Return the available languages as a list of (code, url_code, name,
            active) sorted by name.
        """
        langs = self.with_context(active_test=False).search([])
        return langs.get_sorted()
