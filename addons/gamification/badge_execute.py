from openerp.osv import osv
from openerp.tools.translate import _
from datetime import date


class gamification_badge_execute(osv.AbstractModel):
    """Class that contains the methods to execute for badge granting"""

    _name = 'gamification.badge.execute'
    _description = 'Gamification Badge Execute'

    def nobody(self, cr, uid, context):
        """Return an empty list of users"""
        return []

    def everybody(self, cr, uid, context):
        """Return the id of every user"""
        return self.pool.get('res.users').search(cr, uid, [], context=context)

    def today_users(self, cr, uid, context):
        """Return the list of users that were connected today"""
        domain = [('login_date', '=', date.today().isoformat())]
        return self.pool.get('res.users').search(cr, uid, domain, context=context)

    def long_time_users(self, cr, uid, context, badge_ref=None):
        """Return the list of users that were created at least year ago

        :param badge_ref: the xml reference of a badge, the users having
        already this badge will be excluded
        """
        today = date.today()
        domain = [('create_date', '<=', today.replace(year=today.year-1).isoformat())]

        if badge_ref:
            # retrieve the badge object
            badge = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'gamification', badge_ref)
            if not badge or not badge[1]:
                raise osv.except_osv(_('Error!'), _('Unknown badge reference gamification.%s' % str(badge_ref)))

            # exclude ids of user already having this badge
            badge_user_obj = self.pool.get('gamification.badge.user')
            badge_user_ids = badge_user_obj.search(cr, uid, [('badge_id', '=', badge[1])], context=context)
            excluded_user_ids = [badge_user.user_id.id for badge_user in badge_user_obj.browse(cr, uid, badge_user_ids, context=context)]
            domain.append(('id', 'not in', excluded_user_ids))

        return self.pool.get('res.users').search(cr, uid, domain, context=context)
