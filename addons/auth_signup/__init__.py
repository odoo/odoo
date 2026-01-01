# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models


def _post_init_hook(env):
    _migrate_email_templates_to_body_view(env)


def _migrate_email_templates_to_body_view(env):
    """Set body_view_id on existing templates without clearing body_html.

    This preserves user customizations while enabling view inheritance for new
    installs. Existing body_html takes priority over body_view_id.
    """
    template_view_mapping = [
        ('auth_signup.set_password_email', 'auth_signup.email_body_set_password'),
        ('auth_signup.mail_template_data_unregistered_users', 'auth_signup.email_body_unregistered_users'),
        ('auth_signup.mail_template_user_signup_account_created', 'auth_signup.email_body_user_signup_account_created'),
        ('auth_signup.portal_set_password_email', 'auth_signup.email_body_portal_set_password'),
    ]
    for template_xmlid, view_xmlid in template_view_mapping:
        template = env.ref(template_xmlid, raise_if_not_found=False)
        view = env.ref(view_xmlid, raise_if_not_found=False)
        if template and view and not template.body_view_id:
            template.body_view_id = view
