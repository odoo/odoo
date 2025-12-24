# -*- coding: utf-8 -*-
import os
import logging

_logger = logging.getLogger(__name__)

def configure_mail_server(env):
    """
    Configure mail server settings from environment variables.
    
    Sets up:
    1. Outgoing Mail Server (ir.mail_server)
    2. System Parameters for email (mail.catchall.domain, etc)
    """
    try:
        # Get env vars
        smtp_host = os.getenv('VIA_SUITE_SMTP_HOST', 'email-smtp.us-east-1.amazonaws.com')
        smtp_port = int(os.getenv('VIA_SUITE_SMTP_PORT', '587'))
        smtp_user = os.getenv('VIA_SUITE_SMTP_USER', '')
        smtp_pass = os.getenv('VIA_SUITE_SMTP_PASSWORD', '')
        email_from = os.getenv('VIA_SUITE_EMAIL_FROM', 'no-reply@viafronteira.com')
        
        # 1. Update/Create Mail Server
        mail_server = env.ref('via_suite_base.mail_server_viasuite_ses', raise_if_not_found=False)
        
        if not mail_server:
            # If record doesn't exist (should exist from XML, but just in case)
            # We will search by name or create a new one if completely missing
            mail_server = env['ir.mail_server'].search([
                ('name', '=', 'ViaSuite Amazon SES')
            ], limit=1)
            
        vals = {
            'name': 'ViaSuite Amazon SES',
            'smtp_host': smtp_host,
            'smtp_port': smtp_port,
            'smtp_user': smtp_user,
            'smtp_pass': smtp_pass,
            'smtp_encryption': 'starttls',
            'sequence': 10,
            'active': bool(smtp_user),  # Only active if we have a user
        }
        
        if mail_server:
            mail_server.write(vals)
        else:
            env['ir.mail_server'].create(vals)
            
        # 2. Update System Parameters
        params = {
            'mail.catchall.domain': email_from.split('@')[-1],
            'mail.catchall.alias': email_from.split('@')[0],
            'mail.default.from': email_from,
        }
        
        for key, value in params.items():
            env['ir.config_parameter'].set_param(key, value)
            
        return True
        
    except Exception as e:
        _logger.error(f"Failed to configure mail server: {str(e)}")
        return False
