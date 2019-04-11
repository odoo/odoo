# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging


from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.addons.iap.models import iap
from odoo.addons.mail.wizard.mail_compose_message import _reopen

_logger = logging.getLogger(__name__)

class SMSRecipient(models.TransientModel):
    _name = 'sms.recipient'
    _description = 'SMS Recipient'

    sms_composer_id = fields.Many2one('sms.compose.message')
    partner_id = fields.Many2one('res.partner')
    number = fields.Char(required=True)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for record in self:
            record.number = record.partner_id.mobile if record.partner_id.mobile else record.partner_id.phone

class SendSMS(models.TransientModel):
    _name = 'sms.compose.message'
    _description = 'Send SMS Wizard'

    composition_mode = fields.Selection([('comment', 'Post on a document'), ('mass_sms', 'SMS Mass Mailing')], default='comment')
    use_active_domain = fields.Boolean()

    recipient_ids = fields.One2many('sms.recipient', 'sms_composer_id', string='Recipients')
    model = fields.Char()
    template_id = fields.Many2one('sms.template', string='Use Template', domain="[('model', '=', model)]")
    content = fields.Text(required=True)

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.content = self.template_id.body

    def _get_records(self, model):
        if self.use_active_domain or self.env.context.get('active_domain'):
            records = model.search(self.env.context.get('active_domain'))
        elif self.env.context.get('active_ids'):
            records = model.browse(self.env.context.get('active_ids', []))
        else:
            records = model.browse(self.env.context.get('active_id', []))
        return records

    @api.model
    def default_get(self, fields):
        result = super(SendSMS, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        result['model'] = active_model
        model = self.env[active_model]
        records = self._get_records(model)
        if self.env.context.get('default_composition_mode') != 'mass_sms' \
            and not self.env.context.get('default_recipient_ids'):
            recipients = self.env['sms.sms']._get_sms_recipients(active_model, records.id)
            missing_numbers = []
            for recipient in recipients:
                if not recipient['number']:
                    missing_numbers.append(recipient['partner_id'].display_name)
            if missing_numbers:
                raise UserError(_('Missing mobile number for %s.') % ', '.join(missing_numbers))
            result['recipient_ids'] = [(0, False, {
                'partner_id': recipient['partner_id'] and recipient['partner_id'].id or False,
                'number': recipient['number']
            }) for recipient in recipients]
        if not self.env.context.get('default_template_id'):
            templates_id = self.env['sms.template'].search([('model', '=', active_model)])
            if templates_id:
                result['template_id'] = templates_id[0].id
        return result

    def action_send_sms(self):
        active_model = self.env.context.get('active_model')
        model = self.env[active_model]
        records = self._get_records(model)
        contents = self.template_id._render_template(self.content, active_model, records.ids)
        all_sms = self.env['sms.sms']
        for record in records:
            body = contents.get(record.id)
            values = []
            if self.composition_mode == 'mass_sms':
                # We need to compute the recipients
                for recipient in self.env['sms.sms']._get_sms_recipients(active_model, record.id):
                    partner_id = recipient['partner_id']
                    values.append({
                        'name': partner_id and partner_id.display_name or recipient['number'],
                        'number': recipient['number'],
                        'content': body,
                        'country_id': partner_id and partner_id.country_id and partner_id.country_id.id
                    })
            else:
                # We use the recipients in self.recipient_ids
                for recipient in self.recipient_ids:
                    country_id = recipient.partner_id and recipient.partner_id.country_id and recipient.partner_id.country_id.id
                    values.append({
                        'name': recipient.partner_id.display_name if recipient.partner_id else recipient.number,
                        'number': recipient.number,
                        'content': body,
                        'country_id': country_id
                    })
            sms_ids = self.env['sms.sms'].create(values)
            all_sms |= sms_ids
            if hasattr(record, 'message_post_send_sms'):
                record.message_post_send_sms(body.replace('\n', '<br/>'), sms_ids)
        all_sms._send()
        all_sms._notify_sms_update()

    @api.multi
    def save_as_template(self):
        """ hit save as template button: current form value will be a new
            template attached to the current document. """
        for record in self:
            model = self.env['ir.model']._get(record.model or 'mail.message')
            model_name = model.name or ''
            record_name = False
            if record.composition_mode == 'mass_sms':
                active_model = self.env.context.get('active_model')
                model = self.env[active_model]
                records = self._get_records(model)
                recipients = self.env['sms.sms']._get_sms_recipients(active_model, records and records[0].id)
                record_name = recipients and recipients[0]['partner_id'] and recipients[0]['partner_id'].display_name or 'New Template'
            else:
                record_name = record.recipient_ids and record.recipient_ids[0].partner_id and record.recipient_ids[0].partner_id.display_name or 'New Template'
            template_name = "%s: %s" % (model_name, record_name)
            values = {
                'name': template_name,
                'body': record.content or False,
                'model_id': model.id or False,
            }
            template = self.env['sms.template'].create(values)
            # generate the saved template
            record.write({'template_id': template.id})
            record._onchange_template_id()
            return _reopen(self, record.id, record.model, context=self._context)
