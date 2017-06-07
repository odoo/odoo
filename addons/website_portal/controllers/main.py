# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo import tools
from odoo.tools import pycompat
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import CustomerPortal


class website_account(CustomerPortal):

    def _prepare_portal_values(self):
        values = super(website_account, self)._prepare_portal_layout_values()
        values.update({
            'sales_rep': values['sales_user'],  # compatibility
            # probably not required as those should be already added in eval context
            # 'company': request.website.company_id,
            # 'user': request.env.user
        })
        return values
