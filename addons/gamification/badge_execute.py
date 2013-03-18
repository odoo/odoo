from openerp.osv import osv


class gamification_badge_execute(osv.Model):
    """Class that contains the methods to execute for badge granting"""

    _name = 'gamification.badge.execute'
    _description = 'Gamification Badge Execute'

    def nobody(self, cr, uid, context):
        """Return an empty list of users"""
        return []

    def everybody(self, cr, uid, context):
        """Return the id of every user"""
        return self.pool.get('res.users').search(cr, uid, [], context=context)
