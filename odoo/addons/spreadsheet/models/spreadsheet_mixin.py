# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import zipfile
import base64
import json
import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, MissingError

class SpreadsheetMixin(models.AbstractModel):
    _name = "spreadsheet.mixin"
    _description = "Spreadsheet mixin"
    _auto = False

    spreadsheet_binary_data = fields.Binary(
        required=True,
        string="Spreadsheet file",
        default=lambda self: self._empty_spreadsheet_data_base64(),
    )
    spreadsheet_data = fields.Text(compute='_compute_spreadsheet_data', inverse='_inverse_spreadsheet_data')
    thumbnail = fields.Binary()

    @api.depends("spreadsheet_binary_data")
    def _compute_spreadsheet_data(self):
        attachments = self.env['ir.attachment'].with_context(bin_size=False).search([
            ('res_model', '=', self._name),
            ('res_field', '=', 'spreadsheet_binary_data'),
            ('res_id', 'in', self.ids),
        ])
        data = {
            attachment.res_id: attachment.raw
            for attachment in attachments
        }
        for spreadsheet in self:
            spreadsheet.spreadsheet_data = data.get(spreadsheet.id, False)

    def _inverse_spreadsheet_data(self):
        for spreadsheet in self:
            if not spreadsheet.spreadsheet_data:
                spreadsheet.spreadsheet_binary_data = False
            else:
                spreadsheet.spreadsheet_binary_data = base64.b64encode(spreadsheet.spreadsheet_data.encode())

    @api.onchange('spreadsheet_binary_data')
    def _onchange_data_(self):
        if self.spreadsheet_binary_data:
            try:
                data_str = base64.b64decode(self.spreadsheet_binary_data).decode('utf-8')
                json.loads(data_str)
            except:
                raise ValidationError(_('Invalid JSON Data'))

    def _empty_spreadsheet_data_base64(self):
        """Create an empty spreadsheet workbook.
        Encoded as base64
        """
        data = json.dumps(self._empty_spreadsheet_data())
        return base64.b64encode(data.encode())

    def _empty_spreadsheet_data(self):
        """Create an empty spreadsheet workbook.
        The sheet name should be the same for all users to allow consistent references
        in formulas. It is translated for the user creating the spreadsheet.
        """
        lang = self.env["res.lang"]._lang_get(self.env.user.lang)
        locale = lang._odoo_lang_to_spreadsheet_locale()
        return {
            "version": 1,
            "sheets": [
                {
                    "id": "sheet1",
                    "name": _("Sheet1"),
                }
            ],
            "settings": {
                "locale": locale,
            },
            "revisionId": "START_REVISION",
        }

    def _zip_xslx_files(self, files):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as doc_zip:
            for f in files:
                # to reduce networking load, only the image path is sent.
                # It's replaced by the image content here.
                if 'imageSrc' in f:
                    try:
                        content = self._get_file_content(f['imageSrc'])
                        doc_zip.writestr(f['path'], content)
                    except MissingError:
                        pass
                else:
                    doc_zip.writestr(f['path'], f['content'])

        return stream.getvalue()

    def _get_file_content(self, file_path):
        if file_path.startswith('data:image/png;base64,'):
            return base64.b64decode(file_path.split(',')[1])
        match = re.match(r'/web/image/(\d+)', file_path)
        file_record = self.env['ir.binary']._find_record(
            res_model='ir.attachment',
            res_id=int(match.group(1)),
        )
        return self.env['ir.binary']._get_stream_from(file_record).read()
