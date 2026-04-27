# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _

from . import controllers
from . import models


def _configure_teams(env):
    # Ensure at least one team exists when enabling the module, otherwise create
    # a default one.
    team = env["helpdesk.team"].search([('privacy_visibility', '=', 'portal')], limit=1)  # Default order is sequence, name
    if team:
        team.use_website_helpdesk_form = True
    else:
        team = env["helpdesk.team"].create({
            "name": _("Customer Care (Public)"),
            "stage_ids": False,
            "use_sla": True,
            "member_ids": [Command.link(env.ref('base.user_admin').id)],
            "use_website_helpdesk_form": True,
        })
    team.is_published = True
    team._ensure_website_menu()

    # Ensure that a form template is generated for each helpdesk team using
    # website helpdesk form.
    # Two use cases:
    #   * After manual uninstall/reinstall of the module we have to regenerate
    #     form for concerned teams.
    #   * When the option is selected on a team for the first time, causing the
    #     module to be installed. In that case, the override on write/create
    #     that invokes the form generation does not apply yet and the team does
    #     not get its form generated.
    teams = env['helpdesk.team'].search([('use_website_helpdesk_form', '=', True)])
    teams._ensure_submit_form_view()
