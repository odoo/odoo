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

    def write(self, vals):
        # Sometimes you need to have a method called by both an onchange context and a create/write context. You must
        # not call 'write' when you are in an onchange context but you need to minimize the number of write in other
        # case. This method eases writing on a record by calling either 'update', either 'write' depending the record
        # is a new record or not.
        record = self.record
        in_draft_mode = record != record._origin

        if in_draft_mode:

            new_vals = dict(vals)
            for fieldname, value in vals.items():
                field = record._fields[fieldname]
                if field.type == 'one2many':
                    line_ids_commands = new_vals.pop(fieldname)

                    for command in line_ids_commands:
                        number = command[0]
                        record_id = command[1]

                        if number == 0:
                            self.env[field.comodel_name].new(command[2])
                        elif number == 1:
                            updated_line = record[fieldname].filtered(lambda record: str(record.id) == str(record_id))
                            updated_line.update(command[2])
                        elif number == 2:
                            to_delete_record = record[fieldname].filtered(lambda record: str(record.id) == str(record_id))
                            record[fieldname] -= to_delete_record

            record.update(new_vals)
        else:
            record.write(vals)
