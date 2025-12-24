# -*- coding: utf-8 -*-
"""
Email Template Updater
=======================

Customizes email templates with ViaSuite branding.
"""

import logging

_logger = logging.getLogger(__name__)


class EmailTemplateUpdater:
    """
    Updates email templates with ViaSuite branding.

    Customizes:
    - Email signatures
    - Template headers/footers
    - Color scheme
    - Logo references
    """

    # ViaSuite email footer
    FOOTER_HTML = """
    <div style="margin-top: 20px; padding-top: 20px; border-top: 2px solid #FF730E; text-align: center;">
        <p style="color: #002147; margin: 5px 0;">
            <strong>ViaFronteira, LLC</strong>
        </p>
        <p style="color: #666; font-size: 12px; margin: 5px 0;">
            Retail Management Solutions
        </p>
        <p style="color: #666; font-size: 12px; margin: 5px 0;">
            <a href="https://www.viafronteira.com" style="color: #FF730E;">www.viafronteira.com</a>
        </p>
    </div>
    """

    @classmethod
    def update_auth_signup_template(cls, env):
        """
        Update the password reset email template.

        Args:
            env: Odoo environment
        """
        try:
            template = env.ref('auth_signup.reset_password_email', raise_if_not_found=False)

            if not template:
                _logger.warning("Password reset template not found")
                return

            # Update template body to include ViaSuite branding
            if template.body_html:
                body = template.body_html

                # Replace company references
                body = body.replace('${object.company_id.name}', 'ViaSuite')

                # Add ViaSuite footer if not present
                if 'ViaFronteira, LLC' not in body:
                    body = body.replace('</body>', f'{cls.FOOTER_HTML}</body>')

                template.write({'body_html': body})

                _logger.info("Updated password reset email template")

        except Exception as e:
            _logger.error(f"Error updating auth signup template: {str(e)}")

    @classmethod
    def update_notification_templates(cls, env):
        """
        Update default notification email templates.

        Args:
            env: Odoo environment
        """
        try:
            # Find and update mail notification templates
            templates = env['mail.template'].search([
                '|',
                ('name', 'ilike', 'notification'),
                ('name', 'ilike', 'assigned')
            ])

            for template in templates:
                if not template.body_html:
                    continue

                body = template.body_html
                modified = False

                # Replace Odoo references
                if 'Odoo' in body:
                    body = body.replace('Odoo', 'ViaSuite')
                    modified = True

                # Add ViaSuite footer if not present
                if 'ViaFronteira, LLC' not in body and '</body>' in body:
                    body = body.replace('</body>', f'{cls.FOOTER_HTML}</body>')
                    modified = True

                if modified:
                    template.write({'body_html': body})

            _logger.info(f"Updated {len(templates)} notification templates")

        except Exception as e:
            _logger.error(f"Error updating notification templates: {str(e)}")

    @classmethod
    def set_default_email_from(cls, env):
        """
        Set default email 'from' address for all templates.

        Args:
            env: Odoo environment
        """
        try:
            templates = env['mail.template'].search([])
            default_from = 'no-reply@viafronteira.com'

            for template in templates:
                if not template.email_from or 'odoo' in template.email_from.lower():
                    template.write({'email_from': default_from})

            _logger.info(f"Set default email from for {len(templates)} templates")

        except Exception as e:
            _logger.error(f"Error setting default email from: {str(e)}")

    @classmethod
    def update_all_email_templates(cls, env):
        """
        Update all email templates with ViaSuite branding.

        Args:
            env: Odoo environment
        """
        _logger.info("Starting email template updates...")

        cls.update_auth_signup_template(env)
        cls.update_notification_templates(env)
        cls.set_default_email_from(env)

        _logger.info("Email template updates complete")


def update_email_templates(env):
    """
    Convenience function to update email templates.

    Args:
        env: Odoo environment
    """
    EmailTemplateUpdater.update_all_email_templates(env)