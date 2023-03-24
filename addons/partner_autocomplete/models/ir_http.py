# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """ Add information about iap enrich to perform """
        session_info = super(Http, self).session_info()
        if session_info.get('is_admin'):
            session_info['iap_company_enrich'] = not self.env.user.company_id.iap_enrich_auto_done
        return session_info
