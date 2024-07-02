# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.addons.bus.models.bus_presence import AWAY_TIMER
from odoo.addons.bus.models.bus_presence import DISCONNECTION_TIMER


class ResPartner(models.Model):
    _inherit = 'res.partner'

    im_status = fields.Char('IM Status', compute='_compute_im_status')

    def _compute_im_status(self):
        self.env.cr.execute("""
            SELECT
                U.partner_id as id, MAX(U.forced_im_status) as forced_im_status,
                CASE WHEN max(B.last_poll) IS NULL THEN 'offline'
                    WHEN age(now() AT TIME ZONE 'UTC', max(B.last_poll)) > interval %s THEN 'offline'
                    WHEN age(now() AT TIME ZONE 'UTC', max(B.last_presence)) > interval %s THEN 'away'
                    ELSE 'online'
                END as status
            FROM bus_presence B
            RIGHT JOIN res_users U ON B.user_id = U.id
            WHERE U.partner_id IN %s AND U.active = 't'
         GROUP BY U.partner_id
        """, ("%s seconds" % DISCONNECTION_TIMER, "%s seconds" % AWAY_TIMER, tuple(self.ids)))
        res = {status['id']: (status['status'], status['forced_im_status']) for status in self.env.cr.dictfetchall()}
        for partner in self:
            im_status, forced_im_status = res.get(partner.id, ('im_partner', None))  # if not found, it is a partner, useful to avoid to refresh status in js
            partner.im_status = forced_im_status or im_status
