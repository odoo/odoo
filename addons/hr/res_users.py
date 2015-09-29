from openerp import api
from openerp.osv import fields, osv


class res_users(osv.Model):
    """ Update of res.users class

     - add field for the related employee of the user
     - if adding groups to an user, check if base.group_user is in it (member of
       'Employee'), create an employee form linked to it. """
    _name = 'res.users'
    _inherit = ['res.users']

    _columns = {
        'employee_ids': fields.one2many('hr.employee', 'user_id', 'Related employees'),
    }

    def _message_post_get_eid(self, cr, uid, thread_id, context=None):
        assert thread_id, "res.users does not support posting global messages"
        if context and 'thread_model' in context:
            context = dict(context or {})
            context['thread_model'] = 'hr.employee'
        if isinstance(thread_id, (list, tuple)):
            thread_id = thread_id[0]
        return self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', thread_id)], context=context)

    @api.cr_uid_ids_context
    def message_post(self, cr, uid, thread_id, context=None, **kwargs):
        """ Redirect the posting of message on res.users to the related employee.
            This is done because when giving the context of Chatter on the
            various mailboxes, we do not have access to the current partner_id. """
        if kwargs.get('message_type') == 'email':
            return super(res_users, self).message_post(cr, uid, thread_id, context=context, **kwargs)
        res = None
        employee_ids = self._message_post_get_eid(cr, uid, thread_id, context=context)
        if not employee_ids:  # no employee: fall back on previous behavior
            return super(res_users, self).message_post(cr, uid, thread_id, context=context, **kwargs)
        for employee_id in employee_ids:
            res = self.pool.get('hr.employee').message_post(cr, uid, employee_id, context=context, **kwargs)
        return res
