# -*- coding: utf-8 -*-
from openerp import api, fields, models


class ResUsers(models.Model):

    _inherit = "res.users"

    im_status = fields.Char('IM Status', compute='_compute_im_status')

    @api.multi
    def _compute_im_status(self):
        """ Compute the im_status of the users """
        res = dict((uid, 'offline') for uid in self.ids)
        presences = self.env['bus.presence'].search([('user_id', 'in', self.ids)])
        for presence in presences:
            res[presence.user_id.id] = presence.status
        for user in self:
            user.im_status = res.get(user.id)

    @api.model
    def im_search(self, name, limit=20):
        """ Search users with a name and return its id, name and im_status.
            Note : the user must be logged
            :param name : the user name to search
            :param limit : the limit of result to return
        """
        result = []
        # find the employee group
        group_employee = self.env['ir.model.data'].get_object_reference('base', 'group_user')[1]

        where_clause_base = " U.active = 't' "
        query_params = ()
        if name:
            where_clause_base += " AND P.name ILIKE %s "
            query_params = query_params + ('%'+name+'%',)

        # first query to find online employee
        self._cr.execute('''SELECT U.id as id, P.name as name, COALESCE(S.status, 'offline') as im_status
                FROM bus_presence S
                    JOIN res_users U ON S.user_id = U.id
                    JOIN res_partner P ON P.id = U.partner_id
                WHERE   '''+where_clause_base+'''
                        AND U.id != %s
                        AND EXISTS (SELECT 1 FROM res_groups_users_rel G WHERE G.gid = %s AND G.uid = U.id)
                        AND S.status = 'online'
                ORDER BY P.name
                LIMIT %s
        ''', query_params + (self._uid, group_employee, limit))
        result = result + self._cr.dictfetchall()

        # second query to find other online people
        if len(result) < limit:
            self._cr.execute('''SELECT U.id as id, P.name as name, COALESCE(S.status, 'offline') as im_status
                FROM bus_presence S
                    JOIN res_users U ON S.user_id = U.id
                    JOIN res_partner P ON P.id = U.partner_id
                WHERE   '''+where_clause_base+'''
                        AND U.id NOT IN %s
                        AND S.status = 'online'
                ORDER BY P.name
                LIMIT %s
            ''', query_params + (tuple([u["id"] for u in result]) + (self._uid,), limit-len(result)))
            result = result + self._cr.dictfetchall()

        # third query to find all other people
        if len(result) < limit:
            self._cr.execute('''SELECT U.id as id, P.name as name, COALESCE(S.status, 'offline') as im_status
                FROM res_users U
                    LEFT JOIN bus_presence S ON S.user_id = U.id
                    LEFT JOIN res_partner P ON P.id = U.partner_id
                WHERE   '''+where_clause_base+'''
                        AND U.id NOT IN %s
                ORDER BY P.name
                LIMIT %s
            ''', query_params + (tuple([u["id"] for u in result]) + (self._uid,), limit-len(result)))
            result = result + self._cr.dictfetchall()
        return result
