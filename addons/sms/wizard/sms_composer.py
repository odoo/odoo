# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models, _
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class SendSMS(models.TransientModel):
    _name = 'sms.composer'
    _description = 'Send SMS Wizard'
    _RECIPIENTS_DISPLAY_NBR = 3

    @api.model
    def default_get(self, fields):
        result = super(SendSMS, self).default_get(fields)
        if fields == 'partner_ids':
            # shortcut because default_get in cache, avoid issues
            return result

        result['res_model'] = result.get('res_model') or self.env.context.get('active_model')
        result['composition_mode'] = result.get('composition_mode') or 'comment'

        if result['composition_mode'] == 'comment' and not result.get('res_id'):
            result['res_id'] = self.env.context.get('active_id')
        if result['composition_mode'] != 'comment':
            if result.get('use_active_domain') and not result.get('active_domain'):
                result['active_domain'] = self.env.context['active_domain']
            elif not result.get('res_ids'):
                result['res_ids'] = repr(self.env.context.get('active_ids'))

        if result['res_model']:
            result.update(
                self._get_composer_values(
                    result['composition_mode'], result['res_model'], result.get('res_id'),
                    result.get('body'), result.get('template_id')
                )
            )
        return result

    # documents
    composition_mode = fields.Selection([
        ('numbers', 'Send to numbers'),
        ('comment', 'Post on a document'),
        ('mass', 'Send SMS in batch')],
        string='Composition Mode', default='comment', required=True)
    res_model = fields.Char('Document Model Name')
    res_id = fields.Integer('Document ID')
    res_ids = fields.Char('Document IDs')
    use_active_domain = fields.Boolean('Use active domain')
    active_domain = fields.Text('Active domain', readonly=True)
    # options for comment and mass mode
    mass_keep_log = fields.Boolean('Keep a note on document')
    mass_force_send = fields.Boolean('Send directly')
    # recipients
    recipient_description = fields.Text('Recipients (Partners)', compute='_compute_description')
    recipient_invalid = fields.Text('Invalid recipients', compute='_compute_description')
    number_field_name = fields.Char(string='Field holding number')
    partner_ids = fields.Many2many('res.partner')
    numbers = fields.Char('Recipients (Numbers)')
    sanitized_numbers = fields.Char('Sanitized Number', compute='_compute_sanitized_numbers')
    # content
    template_id = fields.Many2one('sms.template', string='Use Template', domain="[('model', '=', res_model)]")
    body = fields.Text('Message', required=True)

    @api.depends('partner_ids', 'res_model', 'res_id', 'res_ids', 'use_active_domain', 'composition_mode', 'number_field_name', 'sanitized_numbers')
    def _compute_description(self):
        if self.partner_ids:
            description = ''
            description = ','.join('%s - %s' % (partner.display_name, partner.mobile or partner.phone) for partner in self.partner_ids[:self._RECIPIENTS_DISPLAY_NBR])
            if len(self.partner_ids) > self._RECIPIENTS_DISPLAY_NBR:
                description += _(' (and %s more)') % (len(self.partner_ids) - self._RECIPIENTS_DISPLAY_NBR)
            self.recipient_description = description
            self.recipient_invalid = False

        elif self.composition_mode in ('comment', 'mass') and self.res_model:
            records = None
            if self.composition_mode == 'comment' and self.res_id:
                records = self.env[self.res_model].browse(self.res_id)
            elif self.composition_mode == 'mass' and self.res_ids:
                records = self.env[self.res_model].browse(literal_eval(self.res_ids))

            if records and issubclass(type(records), self.pool['mail.thread']):
                res = records._sms_get_recipients_info(force_field=self.number_field_name)
                valid_ids = [rid for rid, rvalues in res.items() if rvalues['sanitized']]
                invalid_ids = [rid for rid, rvalues in res.items() if not rvalues['sanitized']]

                self.recipient_description = ', '.join('%s (%s)' % (
                    res[record.id]['partner'].name or record.display_name,
                    res[record.id]['sanitized'])
                    for record in records if record.id in valid_ids[:self._RECIPIENTS_DISPLAY_NBR]
                ) or False
                if len(valid_ids) > self._RECIPIENTS_DISPLAY_NBR:
                    self.recipient_description += _(', and %s more') % (len(valid_ids) - self._RECIPIENTS_DISPLAY_NBR)

                self.recipient_invalid = ', '.join('%s (%s)' % (
                    res[record.id]['partner'].display_name or record.display_name,
                    res[record.id]['number'])
                    for record in records if record.id in invalid_ids[:self._RECIPIENTS_DISPLAY_NBR]
                ) or False
                if len(invalid_ids) > self._RECIPIENTS_DISPLAY_NBR:
                    self.recipient_description += _(', and %s more') % (len(invalid_ids) - self._RECIPIENTS_DISPLAY_NBR)
            else:
                self.recipient_description = ''
                self.recipient_invalid = '' if self.sanitized_numbers or (self.composition_mode == 'mass' and self.use_active_domain) else _('No record found')

        else:
            self.recipient_description = False

    @api.depends('numbers', 'res_model', 'res_id')
    def _compute_sanitized_numbers(self):
        if self.numbers:
            record = self._get_records() if self.res_model and self.res_id else self.env.user
            sanitize_res = phone_validation.phone_sanitize_numbers_string_w_record(self.numbers, record)
            sanitized_numbers = [info['sanitized'] for info in sanitize_res.values() if info['sanitized']]
            invalid_numbers = [number for number, info in sanitize_res.items() if info['code']]
            if invalid_numbers:
                raise UserError(_('Following numbers are not correctly encoded: %s') % repr(invalid_numbers))
            self.sanitized_numbers = ','.join(sanitized_numbers)
        else:
            self.sanitized_numbers = False

    @api.onchange('composition_mode', 'res_model', 'res_id', 'template_id')
    def _onchange_template_id(self):
        if self.template_id and self.composition_mode == 'comment':
            self.body = self.template_id._render_template(self.template_id.body, self.res_model, [self.res_id])[self.res_id]
        elif self.template_id:
            self.body = self.template_id.body

    # ------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------

    def action_send_sms(self):
        if self.composition_mode in ('numbers', 'comment') and self.recipient_invalid:
            raise UserError(_('Invalid recipients: %s') % self.recipient_invalid)
        self._action_send_sms()
        return False

    def _action_send_sms(self, force_send=False):
        records = self._get_records()
        if self.composition_mode == 'numbers':
            return self._action_send_sms_numbers()
        elif self.composition_mode == 'comment':
            if records is not None and issubclass(type(records), self.pool['mail.thread']):
                return self._action_send_sms_comment(records)
            return self._action_send_sms_numbers()
        elif self.mass_keep_log and records is not None and issubclass(type(records), self.pool['mail.thread']):
            return self._action_send_sms_mass_w_log(records)
        else:
            return self._action_send_sms_mass(records)

    def _action_send_sms_numbers(self):
        self.env['sms.api']._send_sms_batch([{
            'res_id': 0,
            'number': number,
            'content': self.body,
        } for number in self.sanitized_numbers.split(',')])
        return True

    def _action_send_sms_comment(self, records=None):
        records = records if records is not None else self._get_records()
        subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')

        messages = self.env['mail.message']
        for record in records:
            messages |= records._message_sms(
                self.body, subtype_id=subtype_id,
                partner_ids=self.partner_ids.ids or False,
                number_field=self.number_field_name,
                sms_numbers=self.sanitized_numbers.split(',') if self.sanitized_numbers else None)
        return messages

    def _action_send_sms_mass(self, records=None):
        records = records if records is not None else self._get_records()

        record_values = self._prepare_mass_sms_values(records)
        sms_create_vals = [record_values[record.id] for record in records]
        sms = self.env['sms.sms'].sudo().create(sms_create_vals)

        if sms and self.mass_force_send:
            sms.send(auto_commit=False, raise_exception=False)

        return sms

    def _action_send_sms_mass_w_log(self, records=None):
        records = records if records is not None else self._get_records()
        all_bodies = self._prepare_body_values(records=records)
        subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note')

        messages = self.env['mail.message']
        for record in records:
            messages |= record._message_sms(all_bodies[record.id], subtype_id=subtype_id, partner_ids=False, sms_numbers=None, put_in_queue=not self.mass_force_send)
        return messages

    # ------------------------------------------------------------
    # Mass mode specific
    # ------------------------------------------------------------

    def _prepare_recipient_values(self, records=None):
        records = records if records is not None else self._get_records()
        recipients_info = records._sms_get_recipients_info(force_field=self.number_field_name)
        return recipients_info

    def _prepare_body_values(self, records=None):
        records = records if records is not None else self._get_records()
        if self.template_id and self.body == self.template_id.body:
            lang_to_rids = self.template_id._get_ids_per_lang(records.ids)
            all_bodies = {}
            for lang, rids in lang_to_rids.items():
                template = self.template_id.with_context(lang=lang)
                all_bodies.update(template._render_template(template.body, records._name, rids))
        else:
            all_bodies = self.env['mail.template']._render_template(self.body, records._name, records.ids)
        return all_bodies

    def _prepare_mass_sms_values(self, records=None):
        records = records if records is not None else self._get_records()
        all_bodies = self._prepare_body_values(records=records)
        all_recipients = self._prepare_recipient_values(records=records)

        result = {}
        for record in records:
            recipients = all_recipients[record.id]
            result[record.id] = {
                'body': all_bodies[record.id],
                'partner_id': recipients['partner'].id,
                'number': recipients['sanitized'] or recipients['number'],
                'state': 'outgoing' if recipients['sanitized'] else 'error',
            }
        return result

    # ------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------

    def _get_composer_values(self, composition_mode, res_model, res_id, body, template_id):
        result = {}
        if composition_mode == 'comment':
            if not body and template_id:
                template = self.env['sms.template'].browse(template_id)
                result['body'] = template._render_template(template.body, res_model, [res_id])[res_id]
        else:
            if not body and template_id:
                template = self.env['sms.template'].browse(template_id)
                result['body'] = template.body
        return result

    def _get_records(self):
        if not self.res_model:
            return None
        if self.use_active_domain:  # TDE FIXME: clear active_domain (False,[], ..)
            records = self.env[self.res_model].search(safe_eval(self.active_domain))
        elif self.res_id:
            records = self.env[self.res_model].browse(self.res_id)
        else:
            records = self.env[self.res_model].browse(literal_eval(self.res_ids))
        return records
