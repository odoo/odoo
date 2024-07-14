# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import populate
from . import report
from . import wizard


def _create_helpdesk_team(env):
    team_1 = env.ref('helpdesk.helpdesk_team1', raise_if_not_found=False)
    env['res.company'].search([('id', '!=', team_1.company_id.id)])._create_helpdesk_team()
