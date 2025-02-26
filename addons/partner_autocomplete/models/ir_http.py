# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """ Add information about iap enrich to perform """
        session_info = super().session_info()
        if self.env.user._is_admin():
            session_info['iap_company_enrich'] = not self.env.user.company_id.iap_enrich_auto_done
        return session_info
