# Copyright 2020 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models


# based on fields.Binary.write method
def my_write(self, records, value):
    if not self.attachment:
        return super().write(records, value)

    # em230418: somewhere url is converted to bytes() object. Here we convert it back
    if type(value) is bytes:
        value = value.decode("utf-8")

    # discard recomputation of self on records
    records.env.remove_to_compute(self, records)

    # update the cache, and discard the records that are not modified
    cache = records.env.cache
    # em230418: instead of converting to bytes(), like in self.convert_to_cache, we just save string in cache
    cache_value = value
    records = cache.get_records_different_from(records, self, cache_value)
    if not records:
        return records
    if self.store:
        # determine records that are known to be not null
        not_null = cache.get_records_different_from(records, self, None)

    cache.update(records, self, [cache_value] * len(records))

    # retrieve the attachments that store the values, and adapt them
    if self.store and any(records._ids):
        real_records = records.filtered("id")
        atts = records.env["ir.attachment"].sudo()
        if not_null:
            atts = atts.search(
                [
                    ("res_model", "=", self.model_name),
                    ("res_field", "=", self.name),
                    ("res_id", "in", real_records.ids),
                ]
            )
        if value:
            # update the existing attachments
            # em230148: instead of datas - we save to url field and set type field
            atts.write({"url": value, "type": "url"})
            atts_records = records.browse(atts.mapped("res_id"))
            # create the missing attachments
            missing = (real_records - atts_records).filtered("id")
            if missing:
                atts.create(
                    [
                        {
                            "name": self.name,
                            "res_model": record._name,
                            "res_field": self.name,
                            "res_id": record.id,
                            # em230418: changed here start
                            "type": "url",
                            "url": value,
                            # em230418: changed here end
                        }
                        for record in missing
                    ]
                )
        else:
            atts.unlink()
    return records


def my_read(self, records):
    assert self.attachment
    domain = [
        ("res_model", "=", records._name),
        ("res_field", "=", self.name),
        ("res_id", "in", records.ids),
    ]
    data = {
        att.res_id: att.url  # em230418: we read url, instead of datas
        for att in records.env["ir.attachment"].sudo().search(domain)
    }
    cache = records.env.cache
    for record in records:
        cache.set(record, self, data.get(record.id, False))


class Base(models.AbstractModel):

    _inherit = "base"

    def _get_url_fields(self):
        url_fields = self.env.context.get("ir_attachment_url_fields")
        if not url_fields:
            return []
        url_fields = url_fields.split(",")

        result = []
        for full_fname in url_fields:
            if not full_fname:
                continue
            model, fname = full_fname.rsplit(".", 1)
            if self._name == model and fname in self._fields:
                result.append(fname)

        return result

    def write(self, vals):
        url_fields = self._get_url_fields()
        url_fields_values = {}
        for fname in url_fields:
            if fname in vals:
                url_fields_values[fname] = vals.pop(fname)
        res = super(Base, self).write(vals)

        for fname, value in url_fields_values.items():
            my_write(self._fields[fname], self, value)

        return res

    def _read(self, fnames):
        url_fields = self._get_url_fields()
        for fname in filter(lambda fname: fname in fnames, url_fields):
            my_read(self._fields[fname], self)
            fnames.remove(fname)
        return super(Base, self)._read(fnames)

    def with_context(self, *args, **kw):
        url_fields = self._get_url_fields()
        if url_fields:
            self.invalidate_cache(fnames=url_fields)
        return super(Base, self).with_context(*args, **kw)
