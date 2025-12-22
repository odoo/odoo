# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def hierarchy_read(self, domain, fields, parent_field, child_field=None, order=None):
        if parent_field not in fields:
            fields.append(parent_field)
        records = self.search(domain, order=order)
        focus_record = self.env[self._name]
        fetch_child_ids_for_all_records = False
        if not records:
            return []
        elif len(records) == 1:
            domain = [(parent_field, '=', records.id), ('id', '!=', records.id)]
            if records[parent_field]:
                focus_record = records
                records += focus_record[parent_field]
                domain = [('id', 'not in', records.ids), (parent_field, 'in', records.ids)]
            records += self.search(domain, order=order)
        else:
            fetch_child_ids_for_all_records = True
        children_ids_per_record_id = {}
        if not child_field:
            children_ids_per_record_id = {
                record.id: child_ids
                for record, child_ids in self._read_group(
                    [(parent_field, 'in', records.ids if fetch_child_ids_for_all_records else (records - records[parent_field]).ids)],
                    (parent_field,),
                    ('id:array_agg',),
                    order=order
                )
            }
        result = records.read(fields)
        if children_ids_per_record_id:
            for record_data in result:
                if record_data['id'] in children_ids_per_record_id:
                    record_data['__child_ids__'] = children_ids_per_record_id[record_data['id']]
        return result
