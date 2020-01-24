# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LostReason(models.Model):
    _name = "crm.lost.reason"
    _description = 'Opp. Lost Reason'

    name = fields.Char('Description', required=True, translate=True)
    active = fields.Boolean('Active', default=True)

    def name_get(self):
        if self.env.context.get('append_id_to_name', False):
            return [(lost_reason.id, "[{}] {}".format(lost_reason.id, lost_reason.name)) for lost_reason in self]
        else:
            return super(LostReason, self).name_get()
