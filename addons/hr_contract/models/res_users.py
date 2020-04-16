# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class User(models.Model):
    _inherit = ['res.users']

    vehicle = fields.Char(related="employee_id.vehicle")
    bank_account_id = fields.Many2one(related="employee_id.bank_account_id")

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights.
            Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        contract_readable_fields = [
            'vehicle',
            'bank_account_id',
        ]
        init_res = super(User, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = type(self).SELF_READABLE_FIELDS + contract_readable_fields
        return init_res
