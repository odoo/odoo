# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import AccessError, UserError


class PhoneMixin(models.AbstractModel):
    """ Purpose of this mixin is to offer two services

      * compute a sanitized phone number based on ´´_sms_get_number_fields´´.
        It takes first sanitized value, trying each field returned by the
        method (see ``MailThread._sms_get_number_fields()´´ for more details
        about the usage of this method);
      * compute blacklist state of records. It is based on phone.blacklist
        model and give an easy-to-use field and API to manipulate blacklisted
        records;

    Main API methods

      * ``_phone_set_blacklisted``: set recordset as blacklisted;
      * ``_phone_reset_blacklisted``: reactivate recordset (even if not blacklisted
        this method can be called safely);
    """
    _name = 'mail.thread.phone'
    _description = 'Phone Blacklist Mixin'
    _inherit = ['mail.thread']

    phone_sanitized = fields.Char(
        string='Sanitized Number', compute="_compute_phone_sanitized", compute_sudo=True, store=True,
        help="Field used to store sanitized phone number. Helps speeding up searches and comparisons.")
    phone_sanitized_blacklisted = fields.Boolean(
        string='Phone Blacklisted', compute="_compute_blacklisted", compute_sudo=True, store=False,
        search="_search_phone_sanitized_blacklisted", groups="base.group_user",
        help="If the sanitized phone number is on the blacklist, the contact won't receive mass mailing sms anymore, from any list")
    phone_blacklisted = fields.Boolean(
        string='Blacklisted Phone is Phone', compute="_compute_blacklisted", compute_sudo=True, store=False, groups="base.group_user",
        help="Indicates if a blacklisted sanitized phone number is a phone number. Helps distinguish which number is blacklisted \
            when there is both a mobile and phone field in a model.")
    mobile_blacklisted = fields.Boolean(
        string='Blacklisted Phone Is Mobile', compute="_compute_blacklisted", compute_sudo=True, store=False, groups="base.group_user",
        help="Indicates if a blacklisted sanitized phone number is a mobile number. Helps distinguish which number is blacklisted \
            when there is both a mobile and phone field in a model.")

    @api.depends(lambda self: self._phone_get_number_fields())
    def _compute_phone_sanitized(self):
        self._assert_phone_field()
        number_fields = self._phone_get_number_fields()
        for record in self:
            for fname in number_fields:
                sanitized = record.phone_get_sanitized_number(number_fname=fname)
                if sanitized:
                    break
            record.phone_sanitized = sanitized

    @api.depends('phone_sanitized')
    def _compute_blacklisted(self):
        # TODO : Should remove the sudo as compute_sudo defined on methods.
        # But if user doesn't have access to mail.blacklist, doen't work without sudo().
        blacklist = set(self.env['phone.blacklist'].sudo().search([
            ('number', 'in', self.mapped('phone_sanitized'))]).mapped('number'))
        number_fields = self._phone_get_number_fields()
        for record in self:
            record.phone_sanitized_blacklisted = record.phone_sanitized in blacklist
            mobile_blacklisted = phone_blacklisted = False
            # This is a bit of a hack. Assume that any "mobile" numbers will have the word 'mobile'
            # in them due to varying field names and assume all others are just "phone" numbers.
            # Note that the limitation of only having 1 phone_sanitized value means that a phone/mobile number
            # may not be calculated as blacklisted even though it is if both field values exist in a model.
            for number_field in number_fields:
                if 'mobile' in number_field:
                    mobile_blacklisted = record.phone_sanitized_blacklisted and record.phone_get_sanitized_number(number_fname=number_field) == record.phone_sanitized
                else:
                    phone_blacklisted = record.phone_sanitized_blacklisted and record.phone_get_sanitized_number(number_fname=number_field) == record.phone_sanitized
            record.mobile_blacklisted = mobile_blacklisted
            record.phone_blacklisted = phone_blacklisted

    @api.model
    def _search_phone_sanitized_blacklisted(self, operator, value):
        # Assumes operator is '=' or '!=' and value is True or False
        self._assert_phone_field()
        if operator != '=':
            if operator == '!=' and isinstance(value, bool):
                value = not value
            else:
                raise NotImplementedError()

        if value:
            query = """
                SELECT m.id
                    FROM phone_blacklist bl
                    JOIN %s m
                    ON m.phone_sanitized = bl.number AND bl.active
            """
        else:
            query = """
                SELECT m.id
                    FROM %s m
                    LEFT JOIN phone_blacklist bl
                    ON m.phone_sanitized = bl.number AND bl.active
                    WHERE bl.id IS NULL
            """
        self._cr.execute(query % self._table)
        res = self._cr.fetchall()
        if not res:
            return [(0, '=', 1)]
        return [('id', 'in', [r[0] for r in res])]

    def _assert_phone_field(self):
        if not hasattr(self, "_phone_get_number_fields"):
            raise UserError(_('Invalid primary phone field on model %s', self._name))
        if not any(fname in self and self._fields[fname].type == 'char' for fname in self._phone_get_number_fields()):
            raise UserError(_('Invalid primary phone field on model %s', self._name))

    def _phone_get_number_fields(self):
        """ This method returns the fields to use to find the number to use to
        send an SMS on a record. """
        return []

    def _phone_get_country_field(self):
        if 'country_id' in self:
            return 'country_id'
        return False

    def phone_get_sanitized_numbers(self, number_fname='mobile', force_format='E164'):
        res = dict.fromkeys(self.ids, False)
        country_fname = self._phone_get_country_field()
        for record in self:
            number = record[number_fname]
            res[record.id] = phone_validation.phone_sanitize_numbers_w_record([number], record, record_country_fname=country_fname, force_format=force_format)[number]['sanitized']
        return res

    def phone_get_sanitized_number(self, number_fname='mobile', force_format='E164'):
        self.ensure_one()
        country_fname = self._phone_get_country_field()
        number = self[number_fname]
        return phone_validation.phone_sanitize_numbers_w_record([number], self, record_country_fname=country_fname, force_format=force_format)[number]['sanitized']

    def _phone_set_blacklisted(self):
        return self.env['phone.blacklist'].sudo()._add([r.phone_sanitized for r in self])

    def _phone_reset_blacklisted(self):
        return self.env['phone.blacklist'].sudo()._remove([r.phone_sanitized for r in self])

    def phone_action_blacklist_remove(self):
        # wizard access rights currently not working as expected and allows users without access to
        # open this wizard, therefore we check to make sure they have access before the wizard opens.
        can_access = self.env['phone.blacklist'].check_access_rights('write', raise_exception=False)
        if can_access:
            return {
                'name': 'Are you sure you want to unblacklist this Phone Number?',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'phone.blacklist.remove',
                'target': 'new',
            }
        else:
            raise AccessError("You do not have the access right to unblacklist phone numbers. Please contact your administrator.")
