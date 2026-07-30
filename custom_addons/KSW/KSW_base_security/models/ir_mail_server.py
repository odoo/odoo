from odoo import api, models, tools
from odoo.tools.mail import email_normalize, encapsulate_email
import logging

_logger = logging.getLogger(__name__)

class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    @api.model
    def _get_default_from_address(self):
        """Override to use mail.default.from system parameter if set, 
        falling back to CLI config. This ensures strict SMTP servers 
        (like Office 365) don't reject emails due to mismatched sender.
        """
        default_from = self.env['ir.config_parameter'].sudo().get_param('mail.default.from')
        if default_from:
            return default_from
        return super()._get_default_from_address()

    def _prepare_email_message__(self, message, smtp_session):
        """Override to ensure strict From header compliance for Microsoft 365.
        If the envelope sender matches our default authorized email, we force 
        the From header to be encapsulated to avoid SendAsDenied errors.
        """
        _logger.debug("KSW: _prepare_email_message__ called for message from %s", message.get('From'))
        smtp_from, smtp_to_list, message = super()._prepare_email_message__(message, smtp_session)
        
        default_from = self._get_default_from_address()
        normalized_default = email_normalize(default_from)
        normalized_smtp_from = email_normalize(smtp_from)
        
        _logger.debug("KSW: default=%s, smtp_from=%s", normalized_default, normalized_smtp_from)

        if normalized_default and normalized_smtp_from == normalized_default:
            # Always remove Sender header if present as it can trigger SendAsDenied on strict servers
            if 'Sender' in message:
                _logger.info("KSW: Removing Sender header: %s", message['Sender'])
                del message['Sender']

            from_header = message.get('From', '')
            normalized_from = email_normalize(from_header)
            
            if normalized_from != normalized_default:
                _logger.info("KSW: Forcing From header encapsulation for %s via %s", from_header, default_from)
                new_from = encapsulate_email(from_header, default_from)
                
                if 'From' in message:
                    del message['From']
                message['From'] = new_from
                
                # Ensure envelope from is pure email
                smtp_from = normalized_default
                
        return smtp_from, smtp_to_list, message
