# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from . import controllers
from . import models
from . import wizard


def post_init_hook(env):
    # Create a primary calendar for each user
    users = env['res.users'].search([('calendar_users', 'not any', [('is_primary', '=', True)])])
    env['calendar.calendar'].create([
        {
            'calendar_default_privacy': user.res_users_settings_id.calendar_default_privacy or
                env['ir.config_parameter'].sudo().get_str('calendar.default_privacy', 'public'),
            'calendar_users': [Command.create({
                'user_id': user.id,
                'is_primary': True,
                'access_role': 'owner',
                'is_filter_active': True,
                'is_filter_checked': True,
                'label': 'Primary Calendar',
            })],
        }
        for user in users
    ])
    env.flush_all()

    # Link existing events to the user's primary calendar
    env.cr.execute("""
                   UPDATE calendar_event event
                      SET calendar_id = calendar_user.calendar_id
                     FROM calendar_calendar_user calendar_user
                    WHERE event.user_id = calendar_user.user_id
                      AND calendar_user.is_primary = TRUE
                      AND event.calendar_id IS NULL
    """)

    # Link existing recurrences via their base event
    env.cr.execute("""
                   UPDATE calendar_recurrence recurrence
                      SET calendar_id = calendar_user.calendar_id
                     FROM calendar_event event
                            JOIN calendar_calendar_user calendar_user
                                 ON calendar_user.user_id = event.user_id
                                     AND calendar_user.is_primary = TRUE
                    WHERE recurrence.base_event_id = event.id
                      AND recurrence.calendar_id IS NULL
    """)
