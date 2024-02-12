# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools


class Lang(models.Model):
    _inherit = "res.lang"

    @api.model
    @tools.ormcache()
    def get_frontend_langs(self):
        """ Return the languages available in the frontend as a list of
            (code, url_code, name, active) sorted by name.
        """
        langs = self.with_context(active_test=True).search([])
        return langs.get_sorted()

    def get_sorted(self):
        return self.sorted('name').read(['id', 'code', 'url_code', 'name', 'active', 'flag_image_url'])
