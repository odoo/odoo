# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
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
        ('calendar.calendar_template_meeting_invitation', 'calendar.email_body_meeting_invitation'),
        ('calendar.calendar_template_meeting_changedate', 'calendar.email_body_meeting_changedate'),
        ('calendar.calendar_template_meeting_reminder', 'calendar.email_body_meeting_reminder'),
        ('calendar.calendar_template_meeting_update', 'calendar.email_body_meeting_update'),
        ('calendar.calendar_template_delete_event', 'calendar.email_body_delete_event'),
    ]
    for template_xmlid, view_xmlid in template_view_mapping:
        template = env.ref(template_xmlid, raise_if_not_found=False)
        view = env.ref(view_xmlid, raise_if_not_found=False)
        if template and view and not template.body_view_id:
            template.body_view_id = view
