# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.addons.http_routing.models.ir_http import slug


class OnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    #  First step
    @api.model
    def action_open_appointment_onboarding_create_appointment_type(self):
        view_id = self.env.ref('appointment.appointment_type_view_form_appointment_onboarding').id
        existing_appointment = self.env['appointment.type'].search([
            ('create_uid', '=', self.env.uid),
        ], order='create_date desc', limit=1)

        return {
            'name': _('Create your first Appointment'),
            'type': 'ir.actions.act_window',
            'res_id': existing_appointment.id,
            'res_model': 'appointment.type',
            'target': 'new',
            'view_mode': 'form',
            'views': [(view_id, "form")],
            'context': {
                'default_name': _('Meet With Me'),
            }
        }

    # Second step
    @api.model
    def action_open_appointment_onboarding_preview_invite(self):
        view_id = self.env.ref('appointment.appointment_onboarding_link_view_form').id
        appointment_type = self.env['appointment.type'].search([], limit=1) \
            or self.env['appointment.type'].create({'name': _('Meet With Me')})

        return {
            'name': _('Get Your Link'),
            'type': 'ir.actions.act_window',
            'res_model': 'appointment.onboarding.link',
            'target': 'new',
            'view_mode': 'form',
            'views': [(view_id, "form")],
            'context': {
                'default_appointment_type_id': appointment_type.id,
                'default_short_code': slug(appointment_type),
                'dialog_size': 'medium',
            }
        }

    # Third step
    @api.model
    def action_open_appointment_onboarding_configure_calendar_provider(self):
        return {
            'name': _('Connect your Calendar'),
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.provider.config',
            'target': 'new',
            'view_mode': 'form',
            'views': [(False, "form")],
            'context': {
                'dialog_size': 'medium',
            }
        }
