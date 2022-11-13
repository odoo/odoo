# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class PhoneBlackList(models.Model):
    """ Blacklist of phone numbers. Used to avoid sending unwanted messages to people. """
    _name = 'phone.blacklist'
    _inherit = ['mail.thread']
    _description = 'Phone Blacklist'
    _rec_name = 'number'

    number = fields.Char(string='Phone Number', required=True, tracking=True, help='Number should be E164 formatted')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_number', 'unique (number)', 'Number already exists')
    ]

    @api.model_create_multi
    def create(self, values):
        # First of all, extract values to ensure emails are really unique (and don't modify values in place)
        to_create = []
        done = set()
        for value in values:
            number = value['number']
            sanitized_values = phone_validation.phone_sanitize_numbers_w_record([number], self.env.user)[number]
            sanitized = sanitized_values['sanitized']
            if not sanitized:
                raise UserError(sanitized_values['msg'] + _(" Please correct the number and try again."))
            if sanitized in done:
                continue
            done.add(sanitized)
            to_create.append(dict(value, number=sanitized))

        """ To avoid crash during import due to unique email, return the existing records if any """
        sql = '''SELECT number, id FROM phone_blacklist WHERE number = ANY(%s)'''
        numbers = [v['number'] for v in to_create]
        self._cr.execute(sql, (numbers,))
        bl_entries = dict(self._cr.fetchall())
        to_create = [v for v in to_create if v['number'] not in bl_entries]

        results = super(PhoneBlackList, self).create(to_create)
        return self.env['phone.blacklist'].browse(bl_entries.values()) | results

    def write(self, values):
        if 'number' in values:
            number = values['number']
            sanitized_values = phone_validation.phone_sanitize_numbers_w_record([number], self.env.user)[number]
            sanitized = sanitized_values['sanitized']
            if not sanitized:
                raise UserError(sanitized_values['msg'] + _(" Please correct the number and try again."))
            values['number'] = sanitized
        return super(PhoneBlackList, self).write(values)

    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override _search in order to grep search on sanitized number field """
        def use_normalized_value(node, model):
            if node.field == 'number':
                number = node.value
                if isinstance(number, str):
                    sanitized = phone_validation.phone_sanitize_numbers_w_record([number], self.env.user)[number]['sanitized']
                elif isinstance(number, set):
                    sanitized = {
                        v['sanitized']
                        for v in phone_validation.phone_sanitize_numbers_w_record(list(number), self.env.user).values()
                        if v and v['sanitized']
                    }
                else:
                    sanitized = None
                if sanitized and sanitized != number:
                    return expression.D(node.field, node.operator, sanitized)
            return None
        new_args = expression.D(args or []).transform_domain(use_normalized_value)
        return super(PhoneBlackList, self)._search(new_args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    def add(self, number, message=None):
        sanitized = phone_validation.phone_sanitize_numbers_w_record([number], self.env.user)[number]['sanitized']
        return self._add([sanitized], message=message)

    def _add(self, numbers, message=None):
        """ Add or re activate a phone blacklist entry.

        :param numbers: list of sanitized numbers """
        records = self.env["phone.blacklist"].with_context(active_test=False).search([('number', 'in', numbers)])
        todo = [n for n in numbers if n not in records.mapped('number')]
        if records:
            if message:
                records._track_set_log_message(message)
            records.action_unarchive()
        if todo:
            new_records = self.create([{'number': n} for n in todo])
            if message:
                for record in new_records:
                    record.with_context(mail_create_nosubscribe=True).message_post(
                        body=message,
                        subtype_xmlid='mail.mt_note',
                    )
            records += new_records
        return records

    def remove(self, number, message=None):
        sanitized = phone_validation.phone_sanitize_numbers_w_record([number], self.env.user)[number]['sanitized']
        return self._remove([sanitized], message=message)

    def _remove(self, numbers, message=None):
        """ Add de-activated or de-activate a phone blacklist entry.

        :param numbers: list of sanitized numbers """
        records = self.env["phone.blacklist"].with_context(active_test=False).search([('number', 'in', numbers)])
        todo = [n for n in numbers if n not in records.mapped('number')]
        if records:
            if message:
                records._track_set_log_message(message)
            records.action_archive()
        if todo:
            new_records = self.create([{'number': n, 'active': False} for n in todo])
            if message:
                for record in new_records:
                    record.with_context(mail_create_nosubscribe=True).message_post(
                        body=message,
                        subtype_xmlid='mail.mt_note',
                    )
            records += new_records
        return records

    def phone_action_blacklist_remove(self):
        return {
            'name': 'Are you sure you want to unblacklist this Phone Number?',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'phone.blacklist.remove',
            'target': 'new',
        }

    def action_add(self):
        self.add(self.number)
