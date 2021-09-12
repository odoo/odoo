# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def send_mail(self, auto_commit=False):
        result = super(MailComposer, self).send_mail(auto_commit)
        context = self._context
        if context.get('default_model') == 'saas.client':
            saas_client = self.env['saas.client'].browse(context['default_res_id'])
            if saas_client.saas_contract_id:
                saas_client.saas_contract_id.state = "confirm"
                self._cr.commit()
        return result