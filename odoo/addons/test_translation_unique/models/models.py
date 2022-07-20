# -*- coding: utf-8 -*-
import re

from odoo import fields, models, tools, _
from odoo.exceptions import UserError


class TestTranslationUniqueModel1(models.Model):
    _name = 'test.translation.unique.model1'
    _description = 'Translation Test 1'

    name = fields.Char('Name', translate=True)

    def _auto_init(self):
        res = super()._auto_init()
        self.create_unique_index_for_translated_field('name')
        return res

    # TODO
    # run create_unique_index_for_translated_field when activate a new language
    # remove index when necessary

    def create_unique_index_for_translated_field(self, fname):
        field = self._fields[fname]
        if not (field.store and field.translate):
            raise UserError(_('You can use this function only for stored translated fields'))
        for lang_code, lang in self.env['res.lang'].get_installed():
            index_name = f'unique_index_{self._table}_{fname}_{lang_code.lower()}'
            tools.create_unique_index(self.env.cr, index_name, self._table, [f"""(("{fname}"->'{lang_code}'))"""])

    def get_unique_field_value(self, value):
        search_pattern = value + '_copy_[%]'
        re_pattern = value + '(_copy_\[(\d+)\]|)$'

        similar_records = self.with_context(active_test=False).sudo().search([('name', 'ilike', search_pattern)])
        number = 0
        for record in similar_records:
            match = re.match(re_pattern, record.name, re.I | re.M)
            if match:
                number = max(int(match.group(2)), number)
        number = [number]
        def unique_field_value(record=None):
            if record and record.ensure_one() and re.match(re_pattern, record.name, re.I | re.M):
                return record.name
            number[0] = number[0] + 1
            return value + '_copy_' + f'[{number[0]}]'
        return unique_field_value
