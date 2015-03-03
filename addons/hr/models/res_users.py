# -*- coding: utf-8 -*-

from openerp import api, fields, models


class ResUsers(models.Model):
    """ Update of res.users class

     - add field for the related employee of the user
     - if adding groups to an user, check if base.group_user is in it (member of
       'Employee'), create an employee form linked to it. """
    _name = 'res.users'
    _inherit = ['res.users']

    employee_ids = fields.One2many('hr.employee', 'user_id', string='Related employees')
    display_employees_suggestions = fields.Boolean(default=True)

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on
        display_employees_suggestions fields. Access rights are disabled by
        default, but allowed on some specific fields defined in
        self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(ResUsers, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.append('display_employees_suggestions')
        # duplicate list to avoid modifying the original reference
        self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.append('display_employees_suggestions')
        return init_res

    @api.multi
    def stop_showing_employees_suggestions(self):
        """Update display_employees_suggestions value to False"""
        for user in self:
            user.display_employees_suggestions = False

    def _message_post_get_eid(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        if 'thread_model' in ctx:
            ctx['thread_model'] = 'hr.employee'
        return self.env['hr.employee'].with_context(ctx).search([('user_id', '=', self.id)])

    @api.multi
    def message_post(self, **kwargs):
        """ Redirect the posting of message on res.users to the related employee.
            This is done because when giving the context of Chatter on the
            various mailboxes, we do not have access to the current partner_id. """
        self.ensure_one()
        if kwargs.get('type') == 'email':
            return super(ResUsers, self).message_post(**kwargs)
        message_id = None
        employees = self._message_post_get_eid()
        if not employees:  # no employee: fall back on previous behavior
            return super(ResUsers, self).message_post(**kwargs)
        for employee in employees:
            message_id = employee.message_post(**kwargs)
        return message_id
