from openerp.osv import fields, osv
from openerp.tools.translate import _


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
        if context is None:
            context = {}
        self.write(cr, uid, user_id, {"display_employees_suggestions": False}, context)

    def _create_welcome_message(self, cr, uid, user, context=None):
        """Do not welcome new users anymore, welcome new employees instead"""
        return True

    def _message_post_get_eid(self, cr, uid, thread_id, context=None):
        assert thread_id, "res.users does not support posting global messages"
        if context and 'thread_model' in context:
            context = dict(context or {})
            context['thread_model'] = 'hr.employee'
        if isinstance(thread_id, (list, tuple)):
            thread_id = thread_id[0]
        return self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', thread_id)], context=context)

    def message_post(self, cr, uid, thread_id, context=None, **kwargs):
        """ Redirect the posting of message on res.users to the related employee.
            This is done because when giving the context of Chatter on the
            various mailboxes, we do not have access to the current partner_id. """
        if kwargs.get('type') == 'email':
            return super(res_users, self).message_post(cr, uid, thread_id, context=context, **kwargs)
        res = None
        employee_ids = self._message_post_get_eid(cr, uid, thread_id, context=context)
        if not employee_ids:  # no employee: fall back on previous behavior
            return super(res_users, self).message_post(cr, uid, thread_id, context=context, **kwargs)
        for employee_id in employee_ids:
            res = self.pool.get('hr.employee').message_post(cr, uid, employee_id, context=context, **kwargs)
        return res
