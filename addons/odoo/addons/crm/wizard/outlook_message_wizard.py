# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class OutlookMessageWizard(models.TransientModel):
    _name = 'outlook.message.wizard'
    _description = 'Asistente para enviar mensajes por Outlook'

    partner_id = fields.Many2one('res.partner', string='Contacto', required=True, readonly=True)
    partner_name = fields.Char(string='Nombre del contacto', readonly=True)
    email_to = fields.Char(string='Para', required=True)
    email_cc = fields.Char(string='CC')
    subject = fields.Char(string='Asunto', required=True)
    body = fields.Html(string='Mensaje', required=True)
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'outlook_message_wizard_attachment_rel',
        'wizard_id',
        'attachment_id',
        string='Archivos adjuntos'
    )

    def action_send_message(self):
        """Envía el mensaje por correo electrónico usando el sistema de Odoo"""
        self.ensure_one()
        
        # Verificar que el usuario tenga email configurado
        if not self.env.user.email:
            raise UserError(_(
                'Su usuario no tiene una dirección de correo electrónico configurada.\n\n'
                'Por favor, vaya a Ajustes > Usuarios y empresas > Usuarios y configure '
                'su dirección de correo electrónico.'
            ))
        
        try:
            # Preparar los valores del correo
            email_values = {
                'email_from': self.env.user.email,
                'email_to': self.email_to,
                'subject': self.subject,
                'body_html': self.body,
            }
            
            if self.email_cc:
                email_values['email_cc'] = self.email_cc
            
            # Crear el correo usando mail.mail
            mail = self.env['mail.mail'].sudo().create(email_values)
            
            # Agregar archivos adjuntos si existen
            if self.attachment_ids:
                for attachment in self.attachment_ids:
                    mail.attachment_ids = [(4, attachment.id)]
            
            # Intentar enviar el correo
            try:
                mail.send()
                send_status = 'success'
                message = _('El mensaje se ha enviado correctamente a %s') % self.email_to
            except Exception as send_error:
                # Si falla el envío, mantener en cola
                send_status = 'warning'
                message = _(
                    'El mensaje se ha guardado en la cola de correo pero no se pudo enviar inmediatamente.\n\n'
                    'Posible causa: No hay servidor de correo configurado o hay un problema de conexión.\n\n'
                    'El mensaje se enviará automáticamente cuando se configure un servidor de correo '
                    'o puede enviarlo manualmente desde Ajustes > Técnico > Correo electrónico > Correos electrónicos.'
                )
                _logger.warning(f"No se pudo enviar el correo inmediatamente: {str(send_error)}")
            
            # Registrar el mensaje en el chatter del contacto
            self.partner_id.message_post(
                body=self.body,
                subject=self.subject,
                message_type='email',
                subtype_xmlid='mail.mt_comment',
                email_from=self.env.user.email,
                partner_ids=[self.partner_id.id],
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Mensaje procesado') if send_status == 'warning' else _('Mensaje enviado'),
                    'message': message,
                    'type': send_status,
                    'sticky': send_status == 'warning',
                }
            }
            
        except Exception as e:
            _logger.error(f"Error al procesar el mensaje: {str(e)}")
            raise UserError(_(
                'Error al procesar el mensaje: %s'
            ) % str(e))
