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

    def _get_bus_target(self):
        return self.guest_id or super()._get_bus_target()

    def _get_identity_field_name(self):
        return "guest_id" if self.guest_id else super()._get_identity_field_name()

    def _get_identity_data(self):
        self.ensure_one()
        return {"guest_id": self.guest_id.id} if self.guest_id else super()._get_identity_data()

    def _invalidate_im_status(self, fnames=None, flush=True):
        super().invalidate_recordset(fnames, flush)
        self.guest_id.invalidate_recordset(["im_status"])
