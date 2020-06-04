# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.http import request


class Lang(models.Model):
    _inherit = "res.lang"

    @api.model
    def get_available(self):
        """ Return the available languages as a list of (code, name) sorted by
            name.
        """
        if request and request.is_frontend:
            # Only return the active ones in this case
            return self.with_context(active_test=True)._get_sorted_langs_data([])
        return super().get_available()
