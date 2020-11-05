# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MergePartnerAutomatic(models.TransientModel):

    _inherit = 'base.partner.merge.automatic.wizard'

    def _get_ignorable_fields(self):
        """Don't try to merge signup fields"""
        return super()._get_ignorable_fields() + [
            'signup_token', 'signup_type', 'signup_expiration',
        ]
