# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route

class TodoController(Controller):

    @route('/project_todo/new', type='json', auth='user')
    def todo_new_from_systray(self, todo_description, activity_type_id=None, date_deadline=None):
        """ Route to create todo and their activity directly from the systray """
        todo = request.env['project.task'].create({'description': todo_description})
        if date_deadline:
            todo.activity_schedule(
                activity_type_id=activity_type_id or request.env['mail.activity.type'].search([('category', '=', 'reminder')], limit=1).id,
                note=todo.description,
                date_deadline=date_deadline
            )
        return todo.id
