# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class AppointmentSnippets(http.Controller):
    @http.route('/appointment/get_snippet_data', type='json', auth='user')
    def get_snippet_data(self, appointment_type_id=None):
        """
        :param int appointment_type_id: Optional: Only fetch this appointment type's data
        :return: published 'recurring' and 'punctual' category appointment types with their staff users formatted as
          {'id': {
              'id': appointment_type1 id,
              'name': appointment_type1 name,
              'staff_users`: [
                  {'id': user1 id, 'name': user1 name},
                  {'id': user2 id, "name': user2 name},
                  ...users
              ]},
           ...appointments
          }
        """
        domain = [('category', 'in', ['punctual', 'recurring']), ('website_published', '=', True), ('staff_user_ids', '!=', False)]
        if appointment_type_id:
            appointment_types = request.env["appointment.type"].browse(appointment_type_id).filtered_domain(domain)
        else:
            appointment_types = request.env["appointment.type"].search(domain)

        return {
            appointment_type.id: {
                'id': appointment_type.id,
                'name': appointment_type.name,
                'staff_users': appointment_type.staff_user_ids.mapped(lambda user: {'id': user.id, 'name': user.name}),
            } for appointment_type in appointment_types
        }
