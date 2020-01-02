# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.http import request


class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        c = request.env.ref('res.users').get_referral_updates_count_for_current_user()
        values['referral_updates_count'] = c or ''
        values['referral_link'] = request.env.user._get_referral_link()
        return values
