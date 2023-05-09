# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountIncoterms(models.Model):
    _name = 'account.incoterms'
    _description = 'Incoterms'

    name = fields.Char(
        'Name', required=True, translate=True,
        help="Incoterms are series of sales terms. They are used to divide transaction costs and responsibilities between buyer and seller and reflect state-of-the-art transportation practices.")
    code = fields.Char(
        'Code', size=3, required=True,
        help="Incoterm Standard Code")
    active = fields.Boolean(
        'Active', default=True,
        help="By unchecking the active field, you may hide an INCOTERM you will not use.")

    def name_get(self):
        return [(incoterm.id, '%s%s' % (incoterm.code and '[%s] ' % incoterm.code or '', incoterm.name))
                for incoterm in self]
