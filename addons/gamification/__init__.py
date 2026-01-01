# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def _post_init_hook(env):
    _migrate_email_templates_to_body_view(env)


def _migrate_email_templates_to_body_view(env):
    """Set body_view_id on existing templates without clearing body_html.

    This preserves user customizations while enabling view inheritance for new
    installs. Existing body_html takes priority over body_view_id.
    """
    template_view_mapping = [
        ('gamification.email_template_badge_received', 'gamification.email_body_badge_received'),
        ('gamification.email_template_goal_reminder', 'gamification.email_body_goal_reminder'),
        ('gamification.simple_report_template', 'gamification.email_body_simple_report'),
        ('gamification.mail_template_data_new_rank_reached', 'gamification.email_body_new_rank_reached'),
    ]
    for template_xmlid, view_xmlid in template_view_mapping:
        template = env.ref(template_xmlid, raise_if_not_found=False)
        view = env.ref(view_xmlid, raise_if_not_found=False)
        if template and view and not template.body_view_id:
            template.body_view_id = view
