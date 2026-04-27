# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    helpdesk_target_closed = fields.Integer(export_string_translation=False, default=1)
    helpdesk_target_rating = fields.Float(export_string_translation=False, default=4.5)
    helpdesk_target_success = fields.Float(export_string_translation=False, default=85)

    _sql_constraints = [
        ('target_closed_not_zero', 'CHECK(helpdesk_target_closed > 0)', 'You cannot have negative targets'),
        ('target_rating_not_zero', 'CHECK(helpdesk_target_rating > 0)', 'You cannot have negative targets'),
        ('target_success_not_zero', 'CHECK(helpdesk_target_success > 0)', 'You cannot have negative targets'),
    ]

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'helpdesk_target_closed',
            'helpdesk_target_rating',
            'helpdesk_target_success',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'helpdesk_target_closed',
            'helpdesk_target_rating',
            'helpdesk_target_success',
        ]
