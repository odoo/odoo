import re

from . import models  # noqa: F401


def post_init_hook(env):
    """Replace total_overdue by total_overdue_followup in followup email templates."""
    mail_templates = env['account_followup.followup.line'].search([]).mapped('mail_template_id')
    for template in mail_templates:
        template.body_html = re.sub(
            r'''t-out=("([^"]+)|'([^']+))object\.total_overdue\b''',
            r't-out=\1object.total_overdue_followup',
            # unwrap Markup as it cause issue with python <3.12
            str(template.body_html),
        )


def uninstall_hook(env):
    """Restore total_overdue instead of total_overdue_followup in followup email templates."""
    mail_templates = env['account_followup.followup.line'].search([]).mapped('mail_template_id')
    for template in mail_templates:
        template.body_html = re.sub(
            r'''t-out=("([^"]+)|'([^']+))object\.total_overdue_followup\b''',
            r't-out=\1object.total_overdue',
            # unwrap Markup as it cause issue with python <3.12
            str(template.body_html),
        )
