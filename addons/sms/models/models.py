from odoo import models
from odoo.addons.phone_validation.tools import phone_validation


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _sms_get_partner_fields(self):
        """ This method returns the fields to use to find the contact to link
        whensending an SMS. Having partner is not necessary, having only phone
        number fields is possible. However it gives more flexibility to
        notifications management when having partners. """
        fields = []
        if hasattr(self, 'partner_id'):
            fields.append('partner_id')
        if hasattr(self, 'partner_ids'):
            fields.append('partner_ids')
        return fields

    def _sms_get_default_partners(self):
        """ This method will likely need to be overridden by inherited models.
               :returns partners: recordset of res.partner
        """
        partners = self.env['res.partner']
        for fname in self._sms_get_partner_fields():
            partners = partners.union(*self.mapped(fname))  # ensure ordering
        return partners

    def _sms_get_number_fields(self):
        """ This method returns the fields to use to find the number to use to
        send an SMS on a record. """
        if 'mobile' in self:
            return ['mobile']
        return []

    def _sms_get_recipients_info(self, force_field=False, partner_fallback=True):
        """" Get SMS recipient information on current record set. This method
        checks for numbers and sanitation in order to centralize computation.

        Example of use cases

          * click on a field -> number is actually forced from field, find customer
            linked to record, force its number to field or fallback on customer fields;
          * contact -> find numbers from all possible phone fields on record, find
            customer, force its number to found field number or fallback on customer fields;

        :param force_field: either give a specific field to find phone number, either
            generic heuristic is used to find one based on ``_sms_get_number_fields``;
        :param partner_fallback: if no value found in the record, check its customer
            values based on ``_sms_get_default_partners``;

        :return dict: record.id: {
            'partner': a res.partner recordset that is the customer (void or singleton)
                linked to the recipient. See ``_sms_get_default_partners``;
            'sanitized': sanitized number to use (coming from record's field or partner's
                phone fields). Set to False is number impossible to parse and format;
            'number': original number before sanitation;
            'partner_store': whether the number comes from the customer phone fields. If
                False it means number comes from the record itself, even if linked to a
                customer;
            'field_store': field in which the number has been found (generally mobile or
                phone, see ``_sms_get_number_fields``);
        } for each record in self
        """
        result = dict.fromkeys(self.ids, False)
        tocheck_fields = [force_field] if force_field else self._sms_get_number_fields()
        for record in self:
            all_numbers = [record[fname] for fname in tocheck_fields if fname in record]
            all_partners = record._sms_get_default_partners()

            valid_number = False
            for fname in [f for f in tocheck_fields if f in record]:
                valid_number = phone_validation.phone_sanitize_numbers_w_record([record[fname]], record)[record[fname]]['sanitized']
                if valid_number:
                    break

            if valid_number:
                result[record.id] = {
                    'partner': all_partners[0] if all_partners else self.env['res.partner'],
                    'sanitized': valid_number,
                    'number': record[fname],
                    'partner_store': False,
                    'field_store': fname,
                }
            elif all_partners and partner_fallback:
                partner = self.env['res.partner']
                for partner in all_partners:
                    for fname in self.env['res.partner']._sms_get_number_fields():
                        valid_number = phone_validation.phone_sanitize_numbers_w_record([partner[fname]], record)[partner[fname]]['sanitized']
                        if valid_number:
                            break

                if not valid_number:
                    fname = 'mobile' if partner.mobile else ('phone' if partner.phone else 'mobile')

                result[record.id] = {
                    'partner': partner,
                    'sanitized': valid_number if valid_number else False,
                    'number': partner[fname],
                    'partner_store': True,
                    'field_store': fname,
                }
            else:
                # did not find any sanitized number -> take first set value as fallback;
                # if none, just assign False to the first available number field
                value, fname = next(
                    ((value, fname) for value, fname in zip(all_numbers, tocheck_fields) if value),
                    (False, tocheck_fields[0] if tocheck_fields else False)
                )
                result[record.id] = {
                    'partner': self.env['res.partner'],
                    'sanitized': False,
                    'number': value,
                    'partner_store': False,
                    'field_store': fname
                }
        return result
