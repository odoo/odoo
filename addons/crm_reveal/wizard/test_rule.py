# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class TestRule(models.TransientModel):
    _name = "reveal.test.rule"

    ip = fields.Char(string="IP")
    url = fields.Char(string="URL")

    @api.model
    def create(self, vals):
        rec = super(TestRule, self).create(vals)
        self.env['crm.reveal.rule'].process_reveal_request( self.env['http.session'], [vals['url']], vals['ip'])
        # "104.192.139.233"  # "180.211.100.4"  # "208.66.29.178"
        return rec