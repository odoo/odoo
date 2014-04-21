# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class Users(osv.Model):
    _inherit = 'res.users'

    def _cron_moderator_access_update(self, cr, uid, context=None, ids=False):
        """Daily cron check.

        - apply Moderation group for users who have more than 1000 karma.
        """
        modrator_group = self.pool['ir.model.data'].get_object(cr, uid, "website_doc", "group_documentaion_moderator", context=context)
        applicable_user_ids = self.search(cr, uid, [ ('karma', '>=', 1000), ('groups_id', '!=', modrator_group.id)], context=context)
        users = [(4, user) for user in applicable_user_ids]
        self.pool['res.groups'].write(cr, uid, [modrator_group.id], {'users': users}, context=context)
        return True
