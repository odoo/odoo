# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import threading

from odoo import api, fields, models


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    partner_gid = fields.Integer('Company database ID', related="partner_id.partner_gid", inverse="_inverse_partner_gid", store=True)
    iap_enrich_auto_done = fields.Boolean('Enrich Done')

    def _inverse_partner_gid(self):
        for company in self:
            company.partner_id.partner_gid = company.partner_gid

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if not getattr(threading.currentThread(), 'testing', False):
            res.iap_enrich_auto()
        return res

    def iap_enrich_auto(self):
        """ Enrich company. This method should be called by automatic processes
        and a protection is added to avoid doing enrich in a loop. """
        if self.env.user._is_system():
            for company in self.filtered(lambda company: not company.iap_enrich_auto_done):
                company.partner_id._iap_perform_autocomplete(include_logo=True)
            self.iap_enrich_auto_done = True
        return True
