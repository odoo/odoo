# -*- coding: utf-8 -*-
class OrmUtils:

    def __init__(self, record):
        self.record = record
        self.env = record.env

    def cleanup_write_values(self, vals):
        # Since the JS-framework is not sending the minimal diff when saving and the ORM is invalidating the computed
        # fields even when writing the same value as before, we need to cleanup the values to write in order to avoid
        # a huge invalidation of all computed/editable fields.
        cleaned_vals = dict(vals)
        for fieldname, value in vals.items():
            field = self.record._fields[fieldname]

            if field.type == 'many2one':
                if self.record[fieldname].id == vals[fieldname]:
                    del cleaned_vals[fieldname]
            elif field.type == 'many2many':
                current_ids = set(self.record[fieldname].ids)
                after_write_ids = set(self.record.new({fieldname: vals[fieldname]})[fieldname].ids)
                if current_ids == after_write_ids:
                    del cleaned_vals[fieldname]
            elif field.type == 'one2many':
                continue
            elif field.type == 'monetary' and self.record[field.currency_field]:
                if self.record[field.currency_field].is_zero(self.record[fieldname] - vals[fieldname]):
                    del cleaned_vals[fieldname]
            elif self.record[fieldname] == vals[fieldname]:
                del cleaned_vals[fieldname]
        return cleaned_vals
