# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SignRequest(models.Model):

    _inherit = "sign.request"

    def go_to_signable_document(self, request_items=None):
        """ go to the signable document as the signers for specified request_items or the current user"""
        res = super().go_to_signable_document(request_items)
        if not request_items:
            request_items = self.request_item_ids.filtered(lambda r: not r.partner_id or (r.state == 'sent' and r.partner_id.id == self.env.user.partner_id.id))
        if not request_items:
            return res

        res['context']['template_editable'] = res['context']['template_editable'] and request_items[:1].sudo().role_id.auth_method != 'itsme'
        return res
