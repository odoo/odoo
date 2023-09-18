# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.index import unique, Nulls


class BusPresence(models.Model):
    _inherit = ['bus.presence']

    guest_id = fields.Many2one('mail.guest', 'Guest', ondelete='cascade', index=unique(nulls=Nulls.DISTINCT, where='{field} IS NOT NULL'))

    _sql_constraints = [
        ("partner_or_guest_exists", "CHECK((user_id IS NOT NULL AND guest_id IS NULL) OR (user_id IS NULL AND guest_id IS NOT NULL))", "A bus presence must have a user or a guest."),
    ]
