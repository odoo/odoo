# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Sahla Sherin (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': 'GYM Management System',
    'version': '16.0.1.0.0',
    'category': 'Industries',
    'summary': 'GYM Management System For Managing '
               'Membership, Member, Workout Plan, etc',
    'description': 'This module is used for the managing gym we can add '
                   'membership, member, workout plans etc in this module '
                   'basically for managing the membership,member, workout '
                   'plan etc',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': [ 'mail', 'contacts', 'hr',
        'product', 'membership', 'sale_management',
    ],
    'data': [
        'security/gym_mgmt_system_groups.xml',
        'security/ir.model.access.csv',
        'security/gym_mgmt_system_security.xml',
        'data/ir_sequence_data.xml',
        'wizard/assign_workout.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/exercise_for_views.xml',
        'views/gym_exercise_views.xml',
        'views/gym_membership_views.xml',
        'views/measurement_history_views.xml',
        'views/membership_plan_views.xml',
        'views/gym_report_views.xml',
        'views/trainer_skill_views.xml',
        'views/workout_plan_views.xml',
        'views/workout_days_views.xml',
        'views/my_workout_plan_views.xml',
        'views/hr_employee_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
