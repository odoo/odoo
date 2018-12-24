# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request


class PublisherWarrantyController(http.Controller):

    @http.route('/_odoo/update-subscription-status', type='http', auth='user', methods=['GET'])
    def update_subscription_status(self):
        if not request.env.user.has_group('base.group_erp_manager'):
            raise Forbidden()
        ping_cron = request.env.ref('mail.ir_cron_module_update_notification', raise_if_not_found=False)
        if ping_cron:
            ping_cron.sudo().write({'active': True,
                                    'nextcall': datetime.now(),
                                    'numbercall': -1})
            return 'Your subscription status should be updated in a couple of minutes.'
        return 'There was an issue while checking your subscription status. Please contact your support service.'
