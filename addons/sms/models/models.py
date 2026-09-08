from odoo import models


class BaseModel(models.AbstractModel):
    _inherit = "base"

    def _sms_get_recipients_info(self, force_field=False, partner_fallback=True):
        """Get SMS recipient information on current record set. This method
        checks for numbers and sanitation in order to centralize computation.

        Example of use cases

          * click on a field -> number is actually forced from field, find customer
            linked to record, force its number to field or fallback on customer fields;
          * contact -> find numbers from all possible phone fields on record, find
            customer, force its number to found field number or fallback on customer fields;

        :param force_field: either give a specific field to find phone number, either
            generic heuristic is used to find one based on :meth:`_get_phone_number_fields`;
        :param partner_fallback: if no value found in the record, check its customer
            values based on :meth:`_mail_get_partners`;

        :rtype: dict[int, dict[str, Any]]
        :return: a dictionnary with the following structure:

            .. code-block:: python

                {
                    record.id: {
                        # a res.partner recordset that is the customer (void or
                        # singleton) linked to the recipient.
                        # See _mail_get_partners;
                        "partner": ...,
                        # sanitized number to use (coming from record's field
                        # or partner's phone fields). Set to False if number
                        # impossible to parse and format;
                        "sanitized": ...,
                        # original number before sanitation;
                        "number": ...,
                        # whether the number comes from the customer phone
                        # fields. If False it means number comes from the
                        # record itself, even if linked to a customer;
                        "partner_store": ...,
                        # field in which the number has been found (generally
                        # mobile or phone, see _get_phone_number_fields);
                        "field_store": ...,
                    }
                    for record in self
                }

        """
        result = dict.fromkeys(self.ids, False)
        fnames = [force_field] if force_field else self._get_phone_number_fields()
        fnames = [fname for fname in fnames if fname in self._fields]
        field_store = fnames[0] if fnames else False
        partners_by_record = self._mail_get_partners()
        prefetch = self.env["phone.number"].browse()
        for fname in fnames:
            prefetch |= self.mapped(fname)
        for partners in partners_by_record.values():
            prefetch |= partners.mapped("phone_ids")
        prefetch.fetch(["number", "sanitized", "type", "primary", "sequence", "valid"])
        for record in self:
            all_partners = partners_by_record[record.id]
            phone = record._phone_get_numbers(fname=force_field)._primary(
                "mobile", "whatsapp"
            )

            if phone.valid:
                result[record.id] = {
                    "partner": all_partners[0]
                    if all_partners
                    else self.env["res.partner"],
                    "sanitized": phone.sanitized,
                    "number": phone.number,
                    "partner_store": False,
                    "field_store": field_store,
                }
            elif all_partners and partner_fallback:
                partner_phone = self.env["phone.number"]
                for partner in all_partners:
                    partner_phone = partner._phone_get_number("mobile", "whatsapp")
                    if partner_phone.valid:
                        break

                result[record.id] = {
                    "partner": partner,
                    "sanitized": partner_phone.sanitized
                    if partner_phone.valid
                    else False,
                    "number": partner_phone.number or False,
                    "partner_store": True,
                    "field_store": "phone_ids",
                }
            else:
                result[record.id] = {
                    "partner": self.env["res.partner"],
                    "sanitized": False,
                    "number": phone.number or False,
                    "partner_store": False,
                    "field_store": field_store,
                }
        return result
