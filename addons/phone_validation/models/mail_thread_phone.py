# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import UserError


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
    phone_state = fields.Selection([
        ('ok', 'Correct'),
        ('ko', 'Incorrect')], string='State of the phone number', compute="_compute_phone_sanitized", compute_sudo=True, store=True,
        help="Used for processes that need to check the validity of the phone number (e.g: The blacklist /  The CRM predictive lead scoring)")
    phone_blacklisted = fields.Boolean(
        string='Phone Blacklisted', compute="_compute_phone_blacklisted", compute_sudo=True, store=False,
        search="_search_phone_blacklisted", groups="base.group_user",
        help="If the email address is on the blacklist, the contact won't receive mass mailing anymore, from any list")

    @api.depends(lambda self: self._phone_sanitized_depends_fields())
    def _compute_phone_sanitized(self):
        self._assert_phone_field()
        number_fields = self._phone_get_number_fields()
        for record in self:
            phone_sanitized = False
            phone_state = False
            for fname in number_fields:
                sanitized_information = record._phone_get_sanitized_information(number_fname=fname)
                if not phone_sanitized and sanitized_information['sanitized']:
                    phone_sanitized = sanitized_information['sanitized']
                if fname == self._get_phone_state_field():
                    if not sanitized_information['code']:
                        phone_state = 'ok'
                    elif sanitized_information['code'] == 'invalid':
                        phone_state = 'ko'
                    elif sanitized_information['code'] == 'missing_library':  # for clarity
                        phone_state = False

            record.phone_sanitized = phone_sanitized
            record.phone_state = phone_state

    @api.depends('phone_sanitized')
    def _compute_phone_blacklisted(self):
        # TODO : Should remove the sudo as compute_sudo defined on methods.
        # But if user doesn't have access to mail.blacklist, doen't work without sudo().
        blacklist = set(self.env['phone.blacklist'].sudo().search([
            ('number', 'in', self.mapped('phone_sanitized'))]).mapped('number'))
        for record in self:
            record.phone_blacklisted = record.phone_sanitized in blacklist

    @api.model
    def _search_phone_blacklisted(self, operator, value):
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
            raise UserError(_('Invalid primary phone field on model %s') % self._name)
        if not any(fname in self and self._fields[fname].type == 'char' for fname in self._phone_get_number_fields()):
            raise UserError(_('Invalid primary phone field on model %s') % self._name)

    def _phone_get_number_fields(self):
        """ This method returns the fields to use to find the number to use to
        send an SMS on a record. """
        return []

    def _get_phone_state_field(self):
        """ This method returns the field on which the 'phone_state' field will depend. """
        return 'phone'

    def _phone_get_country_field(self):
        if 'country_id' in self:
            return 'country_id'
        return False

    def _phone_sanitized_depends_fields(self):
        """ The phone_sanitized field depends on phone fields + the country field (if defined). """
        depends_fields = self._phone_get_number_fields()
        country_field = self._phone_get_country_field()
        if country_field:
            depends_fields += [country_field]

        return depends_fields

    def phone_get_sanitized_numbers(self, number_fname='mobile', force_format='E164'):
        res = dict.fromkeys(self.ids, False)
        country_fname = self._phone_get_country_field()
        for record in self:
            number = record[number_fname]
            res[record.id] = phone_validation.phone_sanitize_numbers_w_record([number], record, record_country_fname=country_fname, force_format=force_format)[number]['sanitized']
        return res

    def phone_get_sanitized_number(self, number_fname='mobile', force_format='E164'):
        return self._phone_get_sanitized_information(number_fname, force_format)['sanitized']

    def _phone_get_sanitized_information(self, number_fname='mobile', force_format='E164'):
        self.ensure_one()
        country_fname = self._phone_get_country_field()
        number = self[number_fname]
        return phone_validation.phone_sanitize_numbers_w_record([number], self, record_country_fname=country_fname, force_format=force_format)[number]

    def _phone_set_blacklisted(self):
        return self.env['phone.blacklist'].sudo()._add([r.phone_sanitized for r in self])

    def _phone_reset_blacklisted(self):
        return self.env['phone.blacklist'].sudo()._remove([r.phone_sanitized for r in self])
