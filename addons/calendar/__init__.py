# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools import split_every

from . import controllers
from . import models
from . import wizard


def initialize_primary_calendars(env):
    # Create a primary calendar for each user
    BATCH_SIZE = 10000
    previous_last_user = False
    while True:
        # Do not use offset, as each commited batch reduces the number of users to process:
        # ('is_primary', '=', True) will exclude users we already processed in a previous batch
        user_chunk = env['res.users'].with_context(active_test=False).search([
                ('calendar_user_ids', 'not any', [('is_primary', '=', True)]),
                ('share', '=', False),
            ], limit=BATCH_SIZE, order='id asc')

        if not user_chunk or previous_last_user == user_chunk[-1]:
            # failsafe in case we're failing to generate calendars
            break

        previous_last_user = user_chunk[-1]
        user_chunk._generate_primary_calendar()
        env.cr.commit()
