# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _get_examined_html_fields(self):
        """ Returns an array of (model name, field name, domain, requires full
            scan boolean) indicating which HTML field values should be
            examined when using find_in_html_field.
        """
        return [('ir.ui.view', 'arch_db', [('type', '=', 'qweb')], True)]
