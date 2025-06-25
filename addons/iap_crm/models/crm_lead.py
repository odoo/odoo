# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Lead(models.Model):
    _inherit = 'crm.lead'

    reveal_id = fields.Char(string='Reveal ID', index='btree_not_null') # Technical ID of reveal request done by IAP

    def _merge_get_fields(self):
        return super(Lead, self)._merge_get_fields() + ['reveal_id']
