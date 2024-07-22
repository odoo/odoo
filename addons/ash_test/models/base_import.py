from odoo import models

class BaseImport(models.TransientModel):
    _inherit = 'base_import.import'

    def _parse_import_data(self, data, import_fields, options):
        res = super(BaseImport, self)._parse_import_data(data, import_fields, options)
        for record in res:
            if 'custom_field_1' in import_fields:
                record['custom_field_1'] = data[import_fields.index('custom_field_1')]
            if 'custom_field_2' in import_fields:
                record['custom_field_2'] = data[import_fields.index('custom_field_2')]
        return res
