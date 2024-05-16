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

    number = fields.Char(string='Phone Number', required=True, tracking=True, help='Number should be E164 formatted')
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_number', 'unique (number)', 'Number already exists')
    ]

    @api.model_create_multi
    def create(self, values):
        """ Create new (or activate existing) blacklisted numbers.
                A. Note: Attempt to create a number that already exists, but is non-active, will result in its activation.
                B. Note: If the number already exists and it's active, it will be added to returned set, (it won't be re-created)
        Returns Recordset union of created and existing phonenumbers from the requested list of numbers to create
        """
        # Extract and sanitize numbers, ensuring uniques
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

        # Search for existing phone blacklist entries, even inactive ones (will be activated again)
        numbers_requested = [values['number'] for values in to_create]
        existing = self.with_context(active_test=False).search([('number', 'in', numbers_requested)])

        # Out of existing pb records, activate non-active, (unless requested to leave them alone with 'active' set to False)
        numbers_to_keep_inactive = {values['number'] for values in to_create if not values.get('active', True)}
        numbers_to_keep_inactive = numbers_to_keep_inactive & set(existing.mapped('number'))
        existing.filtered(lambda pb: not pb.active and pb.number not in numbers_to_keep_inactive).write({'active': True})

        # Create new records, while skipping existing_numbers
        existing_numbers = set(existing.mapped('number'))
        to_create_filtered = [values for values in to_create if values['number'] not in existing_numbers]
        created = super().create(to_create_filtered)

        # Preserve the original order of numbers requested to create
        numbers_to_id = {record.number: record.id for record in existing | created}
        return self.browse(numbers_to_id[number] for number in numbers_requested)

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
        if args:
            new_args = []
            for arg in args:
                if isinstance(arg, (list, tuple)) and arg[0] == 'number':
                    if isinstance(arg[2], str):
                        number = arg[2]
                        sanitized = phone_validation.phone_sanitize_numbers_w_record([number], self.env.user)[number]['sanitized']
                        search_term = sanitized or number
                    elif isinstance(arg[2], list) and all(isinstance(number, str) for number in arg[2]):
                        search_term = [
                            phone_validation.phone_sanitize_numbers_w_record([number], self.env.user)[number]['sanitized'] or number
                            for number in arg[2]
                        ]
                    else:
                        search_term = arg[2]
                    new_args.append([arg[0], arg[1], search_term])
                else:
                    new_args.append(arg)
        else:
            new_args = args
        return super(PhoneBlackList, self)._search(new_args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    def add(self, number):
        return self._add([number])

    def _add(self, numbers):
        return self.create([{'number': n} for n in numbers])

    def action_remove_with_reason(self, number, reason=None):
        records = self.remove(number)
        if reason:
            for record in records:
                record.message_post(body=_("Unblacklisting Reason: %s", reason))
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
            records.action_archive()
        if todo:
            records += self.create([{'number': n, 'active': False} for n in todo])
        return records

    def phone_action_blacklist_remove(self):
        return {
            'name': _('Are you sure you want to unblacklist this Phone Number?'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'phone.blacklist.remove',
            'target': 'new',
        }

    def action_add(self):
        self.add(self.number)
