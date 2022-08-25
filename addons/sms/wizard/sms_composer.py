# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models, _
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


class SendSMS(models.TransientModel):
    _name = 'sms.composer'
    _description = 'Send SMS Wizard'

    @api.model
    def default_get(self, fields):
        result = super(SendSMS, self).default_get(fields)

        result['res_model'] = result.get('res_model') or self.env.context.get('active_model')

        if not result.get('res_ids'):
            if not result.get('res_id') and self.env.context.get('active_ids') and len(self.env.context.get('active_ids')) > 1:
                result['res_ids'] = repr(self.env.context.get('active_ids'))
        if not result.get('res_id'):
            if not result.get('res_ids') and self.env.context.get('active_id'):
                result['res_id'] = self.env.context.get('active_id')

        return result

    # documents
    composition_mode = fields.Selection([
        ('numbers', 'Send to numbers'),
        ('comment', 'Post on a document'),
        ('mass', 'Send SMS in batch')], string='Composition Mode',
        compute='_compute_composition_mode', precompute=True, readonly=False, required=True, store=True)
    res_model = fields.Char('Document Model Name')
    res_model_description = fields.Char('Document Model Description', compute='_compute_res_model_description')
    res_id = fields.Integer('Document ID')
    res_ids = fields.Char('Document IDs')
    res_ids_count = fields.Integer(
        'Visible records count', compute='_compute_res_ids_count', compute_sudo=False,
        help='Number of recipients that will receive the SMS if sent in mass mode, without applying the Active Domain value')
    comment_single_recipient = fields.Boolean(
        'Single Mode', compute='_compute_comment_single_recipient', compute_sudo=False,
        help='Indicates if the SMS composer targets a single specific recipient')
    # options for comment and mass mode
    mass_keep_log = fields.Boolean('Keep a note on document', default=True)
    mass_force_send = fields.Boolean('Send directly', default=False)
    mass_use_blacklist = fields.Boolean('Use blacklist', default=True)
    # recipients
    recipient_valid_count = fields.Integer('# Valid recipients', compute='_compute_recipients', compute_sudo=False)
    recipient_invalid_count = fields.Integer('# Invalid recipients', compute='_compute_recipients', compute_sudo=False)
    recipient_single_description = fields.Text('Recipients (Partners)', compute='_compute_recipient_single', compute_sudo=False)
    recipient_single_number = fields.Char('Stored Recipient Number', compute='_compute_recipient_single', compute_sudo=False)
    recipient_single_number_itf = fields.Char(
        'Recipient Number', compute='_compute_recipient_single',
        readonly=False, compute_sudo=False, store=True,
        help='Phone number of the recipient. If changed, it will be recorded on recipient\'s profile.')
    recipient_single_valid = fields.Boolean("Is valid", compute='_compute_recipient_single_valid', compute_sudo=False)
    number_field_name = fields.Char('Number Field')
    numbers = fields.Char('Recipients (Numbers)')
    sanitized_numbers = fields.Char('Sanitized Number', compute='_compute_sanitized_numbers', compute_sudo=False)
    # content
    template_id = fields.Many2one('sms.template', string='Use Template', domain="[('model', '=', res_model)]")
    body = fields.Text(
        'Message', compute='_compute_body',
        precompute=True, readonly=False, store=True, required=True)

    @api.depends('res_ids_count')
    @api.depends_context('sms_composition_mode')
    def _compute_composition_mode(self):
        for composer in self:
            if self.env.context.get('sms_composition_mode') == 'guess' or not composer.composition_mode:
                if composer.res_ids_count > 1:
                    composer.composition_mode = 'mass'
                else:
                    composer.composition_mode = 'comment'

    @api.depends('res_model')
    def _compute_res_model_description(self):
        self.res_model_description = False
        for composer in self.filtered('res_model'):
            composer.res_model_description = self.env['ir.model']._get(composer.res_model).display_name

    @api.depends('res_model', 'res_id', 'res_ids')
    def _compute_res_ids_count(self):
        for composer in self:
            composer.res_ids_count = len(literal_eval(composer.res_ids)) if composer.res_ids else 0

    @api.depends('res_id', 'composition_mode')
    def _compute_comment_single_recipient(self):
        for composer in self:
            composer.comment_single_recipient = bool(composer.res_id and composer.composition_mode == 'comment')

    @api.depends('res_model', 'res_id', 'res_ids', 'composition_mode', 'number_field_name', 'sanitized_numbers')
    def _compute_recipients(self):
        for composer in self:
            composer.recipient_valid_count = 0
            composer.recipient_invalid_count = 0

            if composer.composition_mode not in ('comment', 'mass') or not composer.res_model:
                continue

            records = composer._get_records()
            if records and issubclass(type(records), self.pool['mail.thread']):
                res = records._sms_get_recipients_info(force_field=composer.number_field_name, partner_fallback=not composer.comment_single_recipient)
                composer.recipient_valid_count = len([rid for rid, rvalues in res.items() if rvalues['sanitized']])
                composer.recipient_invalid_count = len([rid for rid, rvalues in res.items() if not rvalues['sanitized']])
            else:
                composer.recipient_invalid_count = 0 if (
                    composer.sanitized_numbers or composer.composition_mode == 'mass'
                ) else 1

    @api.depends('res_model', 'number_field_name')
    def _compute_recipient_single(self):
        for composer in self:
            records = composer._get_records()
            if not records or not issubclass(type(records), self.pool['mail.thread']) or not composer.comment_single_recipient:
                composer.recipient_single_description = False
                composer.recipient_single_number = ''
                composer.recipient_single_number_itf = ''
                continue
            records.ensure_one()
            res = records._sms_get_recipients_info(force_field=composer.number_field_name, partner_fallback=False)
            composer.recipient_single_description = res[records.id]['partner'].name or records.display_name
            composer.recipient_single_number = res[records.id]['number'] or ''
            if not composer.recipient_single_number_itf:
                composer.recipient_single_number_itf = res[records.id]['number'] or ''
            if not composer.number_field_name:
                composer.number_field_name = res[records.id]['field_store']

    @api.depends('recipient_single_number', 'recipient_single_number_itf')
    def _compute_recipient_single_valid(self):
        for composer in self:
            value = composer.recipient_single_number_itf or composer.recipient_single_number
            if value:
                records = composer._get_records()
                sanitized = phone_validation.phone_sanitize_numbers_w_record([value], records)[value]['sanitized']
                composer.recipient_single_valid = bool(sanitized)
            else:
                composer.recipient_single_valid = False

    @api.depends('numbers', 'res_model', 'res_id')
    def _compute_sanitized_numbers(self):
        for composer in self:
            if composer.numbers:
                record = composer._get_records() if composer.res_model and composer.res_id else self.env.user
                numbers = [number.strip() for number in composer.numbers.split(',')]
                sanitize_res = phone_validation.phone_sanitize_numbers_w_record(numbers, record)
                sanitized_numbers = [info['sanitized'] for info in sanitize_res.values() if info['sanitized']]
                invalid_numbers = [number for number, info in sanitize_res.items() if info['code']]
                if invalid_numbers:
                    raise UserError(_('Following numbers are not correctly encoded: %s', repr(invalid_numbers)))
                composer.sanitized_numbers = ','.join(sanitized_numbers)
            else:
                composer.sanitized_numbers = False

    @api.depends('composition_mode', 'res_model', 'res_id', 'template_id')
    def _compute_body(self):
        for record in self:
            if record.template_id and record.composition_mode == 'comment' and record.res_id:
                record.body = record.template_id._render_field('body', [record.res_id], compute_lang=True)[record.res_id]
            elif record.template_id:
                record.body = record.template_id.body

    # ------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------

    def action_send_sms(self):
        if self.composition_mode in ('numbers', 'comment'):
            if self.comment_single_recipient and not self.recipient_single_valid:
                raise UserError(_('Invalid recipient number. Please update it.'))
            elif not self.comment_single_recipient and self.recipient_invalid_count:
                raise UserError(_('%s invalid recipients', self.recipient_invalid_count))
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
            if records is None or not issubclass(type(records), self.pool['mail.thread']):
                return self._action_send_sms_numbers()
            if self.comment_single_recipient:
                return self._action_send_sms_comment_single(records)
            else:
                return self._action_send_sms_comment(records)
        else:
            return self._action_send_sms_mass(records)

    def _action_send_sms_numbers(self):
        self.env['sms.api']._send_sms_batch([{
            'res_id': 0,
            'number': number,
            'content': self.body,
        } for number in self.sanitized_numbers.split(',')])
        return True

    def _action_send_sms_comment_single(self, records=None):
        # If we have a recipient_single_original number, it's possible this number has been corrected in the popup
        # if invalid. As a consequence, the test cannot be based on recipient_invalid_count, which count is based
        # on the numbers in the database.
        records = records if records is not None else self._get_records()
        records.ensure_one()
        if self.recipient_single_number_itf and self.recipient_single_number_itf != self.recipient_single_number:
            records.write({self.number_field_name: self.recipient_single_number_itf})
        return self._action_send_sms_comment(records=records)

    def _action_send_sms_comment(self, records=None):
        records = records if records is not None else self._get_records()
        subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')

        messages = self.env['mail.message']
        all_bodies = self._prepare_body_values(records)

        for record in records:
            messages += record._message_sms(
                all_bodies[record.id],
                subtype_id=subtype_id,
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

    def _get_optout_record_ids(self, records, recipients_info):
        """ Compute opt-outed contacts, not necessarily blacklisted. Void by default
        as no opt-out mechanism exist in SMS, see SMS Marketing. """
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
            all_bodies = self.template_id._render_field('body', records.ids, compute_lang=True)
        else:
            all_bodies = self.env['mail.render.mixin']._render_template(self.body, records._name, records.ids)
        return all_bodies

    def _prepare_mass_sms_values(self, records):
        all_bodies = self._prepare_body_values(records)
        all_recipients = self._prepare_recipient_values(records)
        blacklist_ids = self._get_blacklist_record_ids(records, all_recipients)
        optout_ids = self._get_optout_record_ids(records, all_recipients)
        done_ids = self._get_done_record_ids(records, all_recipients)

        result = {}
        for record in records:
            recipients = all_recipients[record.id]
            sanitized = recipients['sanitized']
            if sanitized and record.id in blacklist_ids:
                state = 'canceled'
                failure_type = 'sms_blacklist'
            elif sanitized and record.id in optout_ids:
                state = 'canceled'
                failure_type = 'sms_optout'
            elif sanitized and record.id in done_ids:
                state = 'canceled'
                failure_type = 'sms_duplicate'
            elif not sanitized:
                state = 'canceled'
                failure_type = 'sms_number_format' if recipients['number'] else 'sms_number_missing'
            else:
                state = 'outgoing'
                failure_type = ''

            result[record.id] = {
                'body': all_bodies[record.id],
                'partner_id': recipients['partner'].id,
                'number': sanitized if sanitized else recipients['number'],
                'state': state,
                'failure_type': failure_type,
            }
        return result

    def _prepare_mass_sms(self, records, sms_record_values):
        sms_create_vals = [sms_record_values[record.id] for record in records]
        return self.env['sms.sms'].sudo().create(sms_create_vals)

    def _prepare_log_body_values(self, sms_records_values):
        result = {}
        for record_id, sms_values in sms_records_values.items():
            result[record_id] = html2plaintext(sms_values['body'])
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
        if self.res_ids:
            records = self.env[self.res_model].browse(literal_eval(self.res_ids))
        elif self.res_id:
            records = self.env[self.res_model].browse(self.res_id)
        else:
            records = self.env[self.res_model]

        records = records.with_context(mail_notify_author=True)
        return records
