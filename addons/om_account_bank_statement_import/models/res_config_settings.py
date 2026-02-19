# -*- coding: utf-8 -*-

import odoo
import base64
from odoo import models, api, fields, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sample_import_csv = fields.Binary(default='_default_sample_import_csv')
    sample_import_csv_name = fields.Char(default='Import_Sample.csv')
    sample_import_excel = fields.Binary(default='_default_sample_sheet_excel')
    sample_import_excel_name = fields.Char(default='Import_Sample.xlsx')
    file_name = fields.Char('File', size=64)

    def _default_sample_import_csv(self):
        csv_path = odoo.modules.module.get_resource_path(
            'om_account_bank_statement_import', 'sample_files', 'Import_Sample.csv')
        with open(csv_path, 'rb') as imp_sheet:
            sample_file = imp_sheet.read()
        return sample_file and base64.b64encode(sample_file)

    def _default_sample_sheet_excel(self):
        csv_path = odoo.modules.module.get_resource_path(
            'om_account_bank_statement_import', 'sample_files', 'Import_Sample.xlsx')
        with open(csv_path, 'rb') as imp_sheet:
            sample_file = imp_sheet.read()
        return sample_file and base64.b64encode(sample_file)

    def get_sample_import_csv(self):
        return {
            'name': 'Bank Statement Sample CSV',
            'type': 'ir.actions.act_url',
            'url': ("web/content/?model=" + self._name + "&id=" +
                    str(self.id) + "&filename_field=sample_import_sheet_name&"
                                   "field=sample_import_sheet&download=true&"
                                   "filename=Import_Sample.csv"),
            'target': 'self',
        }

    def get_sample_import_excel(self):
        return {
            'name': 'Bank Statement Sample Excel',
            'type': 'ir.actions.act_url',
            'url': ("web/content/?model=" + self._name + "&id=" +
                    str(self.id) + "&filename_field=sample_import_excel_name&"
                                   "field=sample_import_excel&download=true&"
                                   "filename=Import_Sample.xlsx"),
            'target': 'self',
        }

