# -*- coding: utf-8 -*-

from odoo import fields, models


class BusPresence(models.Model):
    _inherit = ['bus.presence']

    guest_id = fields.Many2one('mail.guest', 'Guest', ondelete='cascade')

    def init(self):
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS bus_presence_guest_unique ON %s (guest_id) WHERE guest_id IS NOT NULL" % self._table)

    _sql_constraints = [
        ("partner_or_guest_exists", "CHECK((user_id IS NOT NULL AND guest_id IS NULL) OR (user_id IS NULL AND guest_id IS NOT NULL))", "A bus presence must have a user or a guest."),
    ]
