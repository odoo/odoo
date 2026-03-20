# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import _


class PhoneBlacklist(models.Model):
    """ Blacklist of phone numbers. Used to avoid sending unwanted messages to people. """
    _name = 'phone.blacklist'
    _inherit = ['mail.thread']
    _description = 'Phone Blacklist'
    _rec_name = 'number'

    number = fields.Char(string='Phone Number', required=True, tracking=True, search='_search_number', help='Number should be E164 formatted')
    active = fields.Boolean(default=True, tracking=True)

    _unique_number = models.Constraint(
        'unique (number)',
        'Number already exists',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """ Create new (or activate existing) blacklisted numbers.
                A. Note: Attempt to create a number that already exists, but is non-active, will result in its activation.
                B. Note: If the number already exists and it's active, it will be added to returned set, (it won't be re-created)
        Returns Recordset union of created and existing phonenumbers from the requested list of numbers to create
        """
        # Extract and sanitize numbers, ensuring uniques
        to_create = []
        done = set()
        for value in vals_list:
            try:
                sanitized_value = self.env.user._phone_format(number=value['number'], raise_exception=True)
            except UserError as err:
                raise UserError(_("%(error)s Please correct the number and try again.", error=err)) from err
            if sanitized_value in done:
                continue
            done.add(sanitized_value)
            to_create.append(dict(value, number=sanitized_value))

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

    def write(self, vals):
        if 'number' in vals:
            try:
                sanitized = self.env.user._phone_format(number=vals['number'], raise_exception=True)
            except UserError as err:
                raise UserError(_("%(error)s Please correct the number and try again.", error=str(err))) from err
            vals['number'] = sanitized
        return super().write(vals)

    def _search_number(self, operator, value):
        sanitize = self.env.user._phone_format
        if operator in ('in', 'not in'):
            value = [sanitize(number=number) or number for number in value]
        else:
            value = sanitize(number=value) or value
        return [('number', operator, value)]

    def add(self, number, message=None):
        sanitized = self.env.user._phone_format(number=number)
        return self._add([sanitized], message=message)

    def _add(self, numbers, message=None):
        """ Add or re activate a phone blacklist entry.

        :param numbers: list of sanitized numbers """

        # Log on existing records
        existing = self.env["phone.blacklist"].with_context(active_test=False).search([('number', 'in', numbers)])
        if existing and message:
            existing._track_set_log_message(message)

        records = self.create([{'number': n} for n in numbers])

        # Post message on new records
        new = records - existing
        if new and message:
            for record in new:
                record.with_context(mail_post_autofollow_author_skip=True).message_post(
                    body=message,
                    subtype_xmlid='mail.mt_note',
                )
        return records

    def remove(self, number, message=None):
        sanitized = self.env.user._phone_format(number=number)
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
                    record.with_context(mail_post_autofollow_author_skip=True).message_post(
                        body=message,
                        subtype_xmlid='mail.mt_note',
                    )
            records += new_records
        return records

    def phone_action_blacklist_remove(self):
        return {
            'name': _('Are you sure you want to unblacklist this phone number?'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'phone.blacklist.remove',
            'target': 'new',
            'context': {'dialog_size': 'medium'},
        }

    def action_add(self):
        self.add(self.number)
