# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, SUPERUSER_ID


class ResUsers(models.Model):
    """ Update of res.users class

     - add field for the related employee of the user
     - if adding groups to an user, check if base.group_user is in it (member of
       'Employee'), create an employee form linked to it. """

    _inherit = 'res.users'

    employee_ids = fields.One2many('hr.employee', 'user_id', string='Related employees')

    @api.multi
    def write(self, vals):
        result = super(ResUsers, self).write(vals)
        Employee = self.env['hr.employee']
        if vals.get('name'):
            for user in self.filtered(lambda user: user.id == SUPERUSER_ID):
                employees = Employee.search([('user_id', '=', user.id)])
                employees.write({'name': vals['name']})
        return result

    @api.multi
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
        if kwargs.get('message_type') == 'email':
            return super(ResUsers, self).message_post(**kwargs)
        message_id = None
        employees = self._message_post_get_eid()
        if not employees:  # no employee: fall back on previous behavior
            return super(ResUsers, self).message_post(**kwargs)
        for employee in employees:
            message_id = employee.message_post(**kwargs)
        return message_id
