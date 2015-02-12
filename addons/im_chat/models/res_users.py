# -*- coding: utf-8 -*-

from openerp.osv import osv, fields



class res_users(osv.osv):
    _inherit = "res.users"

    def _get_im_status(self, cr, uid, ids, fields, arg, context=None):
        """ function computing the im_status field of the users """
        r = dict((i, 'offline') for i in ids)
        status_ids = self.pool['im_chat.presence'].search(cr, uid, [('user_id', 'in', ids)], context=context)
        status = self.pool['im_chat.presence'].browse(cr, uid, status_ids, context=context)
        for s in status:
            r[s.user_id.id] = s.status
        return r

    _columns = {
        'im_status' : fields.function(_get_im_status, type="char", string="IM Status"),
    }

    def im_search(self, cr, uid, name, limit=20, context=None):
        """ search users with a name and return its id, name and im_status """
        result = [];
        # find the employee group
        group_employee = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base', 'group_user')[1]

        where_clause_base = " U.active = 't' "
        query_params = ()
        if name:
            where_clause_base += " AND P.name ILIKE %s "
            query_params = query_params + ('%'+name+'%',)

        # first query to find online employee
        cr.execute('''SELECT U.id as id, P.name as name, COALESCE(S.status, 'offline') as im_status
                FROM im_chat_presence S
                    JOIN res_users U ON S.user_id = U.id
                    JOIN res_partner P ON P.id = U.partner_id
                WHERE   '''+where_clause_base+'''
                        AND U.id != %s
                        AND EXISTS (SELECT 1 FROM res_groups_users_rel G WHERE G.gid = %s AND G.uid = U.id)
                        AND S.status = 'online'
                ORDER BY P.name
                LIMIT %s
        ''', query_params + (uid, group_employee, limit))
        result = result + cr.dictfetchall()

        # second query to find other online people
        if(len(result) < limit):
            cr.execute('''SELECT U.id as id, P.name as name, COALESCE(S.status, 'offline') as im_status
                FROM im_chat_presence S
                    JOIN res_users U ON S.user_id = U.id
                    JOIN res_partner P ON P.id = U.partner_id
                WHERE   '''+where_clause_base+'''
                        AND U.id NOT IN %s
                        AND S.status = 'online'
                ORDER BY P.name
                LIMIT %s
            ''', query_params + (tuple([u["id"] for u in result]) + (uid,), limit-len(result)))
            result = result + cr.dictfetchall()

        # third query to find all other people
        if(len(result) < limit):
            cr.execute('''SELECT U.id as id, P.name as name, COALESCE(S.status, 'offline') as im_status
                FROM res_users U
                    LEFT JOIN im_chat_presence S ON S.user_id = U.id
                    LEFT JOIN res_partner P ON P.id = U.partner_id
                WHERE   '''+where_clause_base+'''
                        AND U.id NOT IN %s
                ORDER BY P.name
                LIMIT %s
            ''', query_params + (tuple([u["id"] for u in result]) + (uid,), limit-len(result)))
            result = result + cr.dictfetchall()
        return result