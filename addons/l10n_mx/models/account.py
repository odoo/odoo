# coding: utf-8
# Copyright 2016 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields


class AccountGoup(models.Model):
    _inherit = 'account.group'

    nature = fields.Selection([
        ('D', 'Debitable Account'), ('A', 'Creditable Account')],
        help='Used in Mexican report of electronic accounting (account nature).')
