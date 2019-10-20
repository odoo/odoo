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

    @api.model
    def default_get(self, fields):
        result = super(SendSMS, self).default_get(fields)
        if fields == 'partner_ids':
            # shortcut because default_get in cache, avoid issues
            return result

        result['res_model'] = result.get('res_model') or self.env.context.get('active_model')
        result['composition_mode'] = result.get('composition_mode')

        # guess the composition mode, if multiples ids => mass composition else comment
        if self.env.context.get('default_composition_mode') and self.env.context.get('default_composition_mode') == "guess":
            if self.env.context.get('active_ids') and len(self.env.context.get('active_ids')) > 1:
                result['composition_mode'] = 'mass'
                result['res_id'] = False
            else:
                result['composition_mode'] = 'comment'
                result['res_ids'] = False

        if not result.get('active_domain'):
            result['active_domain'] = repr(self.env.context.get('active_domain', []))
        if not result.get('res_id'):
            if not result.get('res_ids') and self.env.context.get('active_id'):
                result['res_id'] = self.env.context.get('active_id')
        if not result.get('res_ids'):
            if not result.get('res_id') and self.env.context.get('active_ids'):
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
    res_ids_count = fields.Integer(
        'Visible records count', compute='_compute_recipients_count', compute_sudo=False,
        help='UX field computing the number of recipients in mass mode without active domain')
    use_active_domain = fields.Boolean('Use active domain')
    active_domain = fields.Text('Active domain', readonly=True)
    active_domain_count = fields.Integer(
        'Active records count', compute='_compute_recipients_count', compute_sudo=False,
        help='UX field computing the number of recipients in mass mode based on given active domain')
    # options for comment and mass mode
    mass_keep_log = fields.Boolean('Keep a note on document', default=True)
    mass_force_send = fields.Boolean('Send directly', default=False)
    mass_use_blacklist = fields.Boolean('Use blacklist', default=True)
    # recipients
    recipient_description = fields.Text('Recipients (Partners)', compute='_compute_recipients', compute_sudo=False)
    recipient_count = fields.Integer('# Valid recipients', compute='_compute_recipients', compute_sudo=False)
    recipient_invalid_count = fields.Integer('# Invalid recipients', compute='_compute_recipients', compute_sudo=False)
    number_field_name = fields.Char(string='Field holding number')
    partner_ids = fields.Many2many('res.partner')
    numbers = fields.Char('Recipients (Numbers)')
    sanitized_numbers = fields.Char('Sanitized Number', compute='_compute_sanitized_numbers', compute_sudo=False)
    # content
    template_id = fields.Many2one('sms.template', string='Use Template', domain="[('model', '=', res_model)]")
    body = fields.Text('Message', required=True)

    @api.depends('res_model', 'res_ids', 'active_domain')
    def _compute_recipients_count(self):
        self.res_ids_count = len(literal_eval(self.res_ids)) if self.res_ids else 0
        if self.res_model:
            self.active_domain_count = self.env[self.res_model].search_count(safe_eval(self.active_domain or '[]'))
        else:
            self.active_domain_count = 0

    @api.depends('partner_ids', 'res_model', 'res_id', 'res_ids', 'use_active_domain', 'composition_mode', 'number_field_name', 'sanitized_numbers')
    def _compute_recipients(self):
        self.recipient_description = False
        self.recipient_count = 0
        self.recipient_invalid_count = 0

        if self.partner_ids:
            if len(self.partner_ids) == 1:
                self.recipient_description = '%s (%s)' % (self.partner_ids[0].display_name, self.partner_ids[0].mobile or self.partner_ids[0].phone or _('Missing number'))
            self.recipient_count = len(self.partner_ids)

        elif self.composition_mode in ('comment', 'mass') and self.res_model:
            records = self._get_records()

            if records and issubclass(type(records), self.pool['mail.thread']):
                res = records._sms_get_recipients_info(force_field=self.number_field_name)
                valid_ids = [rid for rid, rvalues in res.items() if rvalues['sanitized']]
                invalid_ids = [rid for rid, rvalues in res.items() if not rvalues['sanitized']]
                self.recipient_count = len(valid_ids)
                self.recipient_invalid_count = len(invalid_ids)
                if len(records) == 1:
                    self.recipient_description = '%s (%s)' % (
                        res[records.id]['partner'].name or records.display_name,
                        res[records.id]['sanitized'] or _("Invalid number")
                    )
            else:
                self.recipient_invalid_count = 0 if (self.sanitized_numbers or (self.composition_mode == 'mass' and self.use_active_domain)) else 1

    @api.depends('numbers', 'res_model', 'res_id')
    def _compute_sanitized_numbers(self):
        if self.numbers:
            record = self._get_records() if self.res_model and self.res_id else self.env.user
            numbers = [number.strip() for number in self.numbers.split(',')]
            sanitize_res = phone_validation.phone_sanitize_numbers_w_record(numbers, record)
            sanitized_numbers = [info['sanitized'] for info in sanitize_res.values() if info['sanitized']]
            invalid_numbers = [number for number, info in sanitize_res.items() if info['code']]
            if invalid_numbers:
                raise UserError(_('Following numbers are not correctly encoded: %s') % repr(invalid_numbers))
            self.sanitized_numbers = ','.join(sanitized_numbers)
        else:
            self.sanitized_numbers = False

    @api.onchange('composition_mode', 'res_model', 'res_id', 'template_id')
    def _onchange_template_id(self):
        if self.template_id and self.composition_mode == 'comment' and self.res_id:
            self.body = self.template_id._get_translated_bodies([self.res_id])[self.res_id]
        elif self.template_id:
            self.body = self.template_id.body

    # ------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------

    def action_send_sms(self):
        if self.composition_mode in ('numbers', 'comment') and self.recipient_invalid_count:
            raise UserError(_('%s invalid recipients') % self.recipient_invalid_count)
        self._action_send_sms()
        return False

    def action_send_sms_mass_now(self):
        if not self.mass_force_send:
            self.write({'mass_force_send': True})
        return self.action_send_sms()

    def _action_send_sms(self):
        records = self._get_records()
        if self.composition_mode == 'numbers':
            return self._action_send_sms_numbers()
        elif self.composition_mode == 'comment':
            if records is not None and issubclass(type(records), self.pool['mail.thread']):
                return self._action_send_sms_comment(records)
            return self._action_send_sms_numbers()
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
        subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note')

        messages = self.env['mail.message']
        for record in records:
            messages |= record._message_sms(
                self.body, subtype_id=subtype_id,
                partner_ids=self.partner_ids.ids or False,
                number_field=self.number_field_name,
                sms_numbers=self.sanitized_numbers.split(',') if self.sanitized_numbers else None)
        return messages

    def _action_send_sms_mass(self, records=None):
        records = records if records is not None else self._get_records()

        sms_record_values = self._prepare_mass_sms_values(records)
        sms_all = self._prepare_mass_sms(records, sms_record_values)

        if sms_all and self.mass_keep_log and records and issubclass(type(records), self.pool['mail.thread']):
            log_values = self._prepare_mass_log_values(records, sms_record_values)
            records._message_log_batch(**log_values)

        if sms_all and self.mass_force_send:
            sms_all.filtered(lambda sms: sms.state == 'outgoing').send(auto_commit=False, raise_exception=False)
            return self.env['sms.sms'].sudo().search([('id', 'in', sms_all.ids)])
        return sms_all

    # ------------------------------------------------------------
    # Mass mode specific
    # ------------------------------------------------------------

    def _get_blacklist_record_ids(self, records, recipients_info):
        """ Get a list of blacklisted records. Those will be directly canceled
        with the right error code. """
        if self.mass_use_blacklist:
            bl_numbers = self.env['phone.blacklist'].sudo().search([]).mapped('number')
            return [r.id for r in records if recipients_info[r.id]['sanitized'] in bl_numbers]
        return []

    def _get_done_record_ids(self, records, recipients_info):
        """ Get a list of already-done records. Order of record set is used to
        spot duplicates so pay attention to it if necessary. """
        done_ids, done = [], []
        for record in records:
            sanitized = recipients_info[record.id]['sanitized']
            if sanitized in done:
                done_ids.append(record.id)
            else:
                done.append(sanitized)
        return done_ids

    def _prepare_recipient_values(self, records):
        recipients_info = records._sms_get_recipients_info(force_field=self.number_field_name)
        return recipients_info

    def _prepare_body_values(self, records):
        if self.template_id and self.body == self.template_id.body:
            all_bodies = self.template_id._get_translated_bodies(records.ids)
        else:
            all_bodies = self.env['mail.template']._render_template(self.body, records._name, records.ids)
        return all_bodies

    def _prepare_mass_sms_values(self, records):
        all_bodies = self._prepare_body_values(records)
        all_recipients = self._prepare_recipient_values(records)
        blacklist_ids = self._get_blacklist_record_ids(records, all_recipients)
        done_ids = self._get_done_record_ids(records, all_recipients)

        result = {}
        for record in records:
            recipients = all_recipients[record.id]
            sanitized = recipients['sanitized']
            if sanitized and record.id in blacklist_ids:
                state = 'canceled'
                error_code = 'sms_blacklist'
            elif sanitized and record.id in done_ids:
                state = 'canceled'
                error_code = 'sms_duplicate'
            elif not sanitized:
                state = 'error'
                error_code = 'sms_number_format' if recipients['number'] else 'sms_number_missing'
            else:
                state = 'outgoing'
                error_code = ''

            result[record.id] = {
                'body': all_bodies[record.id],
                'partner_id': recipients['partner'].id,
                'number': sanitized if sanitized else recipients['number'],
                'state': state,
                'error_code': error_code,
            }
        return result

    def _prepare_mass_sms(self, records, sms_record_values):
        sms_create_vals = [sms_record_values[record.id] for record in records]
        return self.env['sms.sms'].sudo().create(sms_create_vals)

    def _prepare_log_body_values(self, sms_records_values):
        result = {}
        for record_id, sms_values in sms_records_values.items():
            result[record_id] = sms_values['body']
        return result

    def _prepare_mass_log_values(self, records, sms_records_values):
        return {
            'bodies': self._prepare_log_body_values(sms_records_values),
            'message_type': 'sms',
        }

    # ------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------

    def _get_composer_values(self, composition_mode, res_model, res_id, body, template_id):
        result = {}
        if composition_mode == 'comment':
            if not body and template_id and res_id:
                template = self.env['sms.template'].browse(template_id)
                result['body'] = template._render_template(template.body, res_model, [res_id])[res_id]
            elif template_id:
                template = self.env['sms.template'].browse(template_id)
                result['body'] = template.body
        else:
            if not body and template_id:
                template = self.env['sms.template'].browse(template_id)
                result['body'] = template.body
        return result

    def _get_records(self):
        if not self.res_model:
            return None
        if self.use_active_domain:
            active_domain = safe_eval(self.active_domain or '[]')
            records = self.env[self.res_model].search(active_domain)
        elif self.res_id:
            records = self.env[self.res_model].browse(self.res_id)
        else:
            records = self.env[self.res_model].browse(literal_eval(self.res_ids or '[]'))
        return records
