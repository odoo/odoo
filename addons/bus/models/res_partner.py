# -*- coding: utf-8 -*-
from openerp import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    im_status = fields.Char('IM Status', compute='_compute_im_status')

    @api.multi
    def _compute_im_status(self):
        self.env.cr.execute("""
            SELECT P.id as id, B.status as im_status
            FROM bus_presence B
                JOIN res_users U ON B.user_id = U.id
                JOIN res_partner P ON P.id = U.partner_id
            WHERE P.id IN %s AND U.active = 't'
        """, (tuple(self.ids),))
        fetch_result = self.env.cr.dictfetchall()
        result = dict(((user_presence['id'], user_presence['im_status']) for user_presence in fetch_result))
        for partner in self:
            partner.im_status = result.get(partner.id, 'offline')

    @api.model
    def im_search(self, name, limit=20):
        """ Search partner with a name and return its id, name and im_status.
            Note : the user must be logged
            :param name : the partner name to search
            :param limit : the limit of result to return
        """
        name = '%' + name + '%'
        excluded_partner_ids = [self.env.user.partner_id.id]
        self.env.cr.execute("""
            SELECT U.id as user_id, P.id as id, P.name as name, COALESCE(B.status, 'offline') as im_status
            FROM res_users U
                JOIN res_partner P ON P.id = U.partner_id
                LEFT JOIN bus_presence B ON B.user_id = U.id
            WHERE P.name ILIKE %s
                AND P.id NOT IN %s
                AND U.active = 't'
            LIMIT %s
        """, (name, tuple(excluded_partner_ids), limit))
        result = self.env.cr.dictfetchall()
        return result
