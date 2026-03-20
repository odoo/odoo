# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.mass_mailing.controllers import main


class MassMailController(main.MassMailController):

    def _get_value(self, subscription_type):
        value = super(MassMailController, self)._get_value(subscription_type)
        if not value and subscription_type == 'mobile':
            if not request.env.user._is_public():
                value = request.env.user.partner_id.phone
            elif request.session.get('mass_mailing_mobile'):
                value = request.session['mass_mailing_mobile']
        return value

    def _get_fname(self, subscription_type):
        value_field = super(MassMailController, self)._get_fname(subscription_type)
        if not value_field and subscription_type == 'mobile':
            value_field = 'mobile'
        return value_field
