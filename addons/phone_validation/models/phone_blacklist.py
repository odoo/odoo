# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PhoneBlackList(models.Model):
    """ Blacklist of phone numbers. Used to avoid sending unwanted messages to people. """
    _name = 'phone.blacklist'
    _inherit = ['mail.thread']
    _description = 'Phone Blacklist'
    _rec_name = 'number'

    number = fields.Char(string='Phone Number', required=True, index=True, tracking=True, help='Number should be E164 formatted')
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
            sanitized = phone_validation.phone_sanitize_numbers_w_record([number], self.env.user)[number]['sanitized']
            if not sanitized:
                raise UserError(_('Invalid number %s') % number)
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
            sanitized = phone_validation.phone_sanitize_numbers_w_record([number], self.env.user)[number]['sanitized']
            if not sanitized:
                raise UserError(_('Invalid number %s') % number)
            values['number'] = sanitized
        return super(PhoneBlackList, self).write(values)

    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override _search in order to grep search on sanitized number field """
        if args:
            new_args = []
            for arg in args:
                if isinstance(arg, (list, tuple)) and arg[0] == 'number' and isinstance(arg[2], str):
                    number = arg[2]
                    sanitized = phone_validation.phone_sanitize_numbers_w_record([number], self.env.user)[number]['sanitized']
                    if sanitized:
                        new_args.append([arg[0], arg[1], sanitized])
                    else:
                        new_args.append(arg)
                else:
                    new_args.append(arg)
        else:
            new_args = args
        return super(PhoneBlackList, self)._search(new_args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    def add(self, number):
        sanitized = phone_validation.phone_sanitize_numbers_w_record([number], self.env.user)[number]['sanitized']
        return self._add([sanitized])

    def _add(self, numbers):
        """ Add or re activate a phone blacklist entry.

        :param numbers: list of sanitized numbers """
        records = self.env["phone.blacklist"].with_context(active_test=False).search([('number', 'in', numbers)])
        todo = [n for n in numbers if n not in records.mapped('number')]
        if records:
            records.write({'active': True})
        if todo:
            records += self.create([{'number': n} for n in todo])
        return records

    def remove(self, number):
        sanitized = phone_validation.phone_sanitize_numbers_w_record([number], self.env.user)[number]['sanitized']
        return self._remove([sanitized])

    def _remove(self, numbers):
        """ Add de-activated or de-activate a phone blacklist entry.

        :param numbers: list of sanitized numbers """
        records = self.env["phone.blacklist"].with_context(active_test=False).search([('number', 'in', numbers)])
        todo = [n for n in numbers if n not in records.mapped('number')]
        if records:
            records.write({'active': False})
        if todo:
            records += self.create([{'number': n, 'active': False} for n in todo])
        return records
