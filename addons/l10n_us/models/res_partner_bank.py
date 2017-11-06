# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    aba_routing = fields.Integer(string="ABA/Routing", help="American Bankers Association Routing Number")

    def _check_aba_routing(self, aba_routing):
        if aba_routing and not re.match(r'^\d{1,9}$', aba_routing):
            raise UserError(_('ABA/Routing should only contains numbers (maximum 9 digits).'))
        return aba_routing

    # ONLY FOR v11. DO NOT FORWARDPORT!
    @api.model
    def create(self, vals):
        if vals.get('aba_routing'):
            vals['aba_routing'] = int(self._check_aba_routing(vals['aba_routing']))
        return super(ResPartnerBank, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('aba_routing'):
            vals['aba_routing'] = int(self._check_aba_routing(vals['aba_routing']))
        return super(ResPartnerBank, self).write(vals)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        result = super(ResPartnerBank, self).read(fields, load=load)
        for record in result:
            if record.get('aba_routing'):
                record['aba_routing'] = str(record['aba_routing'])
        return result
