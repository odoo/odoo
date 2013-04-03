from openerp.osv import fields, osv


class res_users(osv.Model):
    """ Update of res.users class
        - if adding groups to an user, check if base.group_user is in it
        (member of 'Employee'), create an employee form linked to it.
    """
    _name = 'res.users'
    _inherit = ['res.users']

    _columns = {
        'display_employees_suggestions': fields.boolean("Display Employees Suggestions"),
    }

    _defaults = {
        'display_employees_suggestions': True,
    }

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on 
        display_employees_suggestions fields. Access rights are disabled by
        default, but allowed on some specific fields defined in
        self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(res_users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.append('display_employees_suggestions')
        # duplicate list to avoid modifying the original reference
        self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.append('display_employees_suggestions')
        return init_res

    def stop_showing_employees_suggestions(self, cr, uid, user_id, context=None):
        """Update display_employees_suggestions value to False"""
        if context is None: context = {}
        self.write(cr, uid, user_id, {"display_employees_suggestions": False}, context)
