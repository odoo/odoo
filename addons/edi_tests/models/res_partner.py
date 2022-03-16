# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'edi.document.mixin']

    def _do_something_creating_edi_flows(self):
        self._hook_initiate_flows(self)

    def _do_something_canceling_edi_flows(self):
        self.ensure_one()
        self._hook_request_flow_cancellation()

    def _hook_initiate_flows(self, documents):
        super()._hook_initiate_flows(documents)
        self._create_flow_for_format_code('edi_test', documents)
