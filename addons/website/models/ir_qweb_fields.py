# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class Contact(models.AbstractModel):
    _inherit = 'ir.qweb.field.contact'

    @api.model
    def get_available_options(self):
        options = super(Contact, self).get_available_options()
        options.update(
            website_description={'type': 'boolean', 'string': _('Display the website description')},
            UserBio={'type': 'boolean', 'string': _('Display the biography')},
            badges={'type': 'boolean', 'string': _('Display the badges')}
        )
        return options
