# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo import SUPERUSER_ID


class User(models.Model):

    _inherit = ['res.users']

    employee_ids = fields.One2many('hr.employee', 'user_id', string='Related employees')

    @api.multi
    def write(self, vals):
        """ When renaming admin user, we want its new name propagated to its related employees """
        result = super(User, self).write(vals)
        Employee = self.env['hr.employee']
        if vals.get('name'):
            for user in self.filtered(lambda user: user.id == SUPERUSER_ID):
                employees = Employee.search([('user_id', '=', user.id)])
                employees.write({'name': vals['name']})
        return result

    @api.multi
    def _get_related_employees(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        if 'thread_model' in ctx:
            ctx['thread_model'] = 'hr.employee'
        return self.env['hr.employee'].with_context(ctx).search([('user_id', '=', self.id)])

    @api.multi
    @api.returns('self', lambda value: value.id)
    def message_post(self, **kwargs):
        """ Redirect the posting of message on res.users to the related employees.
            This is done because when giving the context of Chatter on the
            various mailboxes, we do not have access to the current partner_id.
        """
        self.ensure_one()
        if kwargs.get('message_type') == 'email':
            return super(User, self).message_post(**kwargs)
        message_id = None
        employees = self._get_related_employees()
        if not employees:  # no employee: fall back on previous behavior
            return super(User, self).message_post(**kwargs)
        for employee in employees:
            message_id = employee.message_post(**kwargs)
        return message_id
