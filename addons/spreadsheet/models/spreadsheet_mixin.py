# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import zipfile
import base64
import json
import re

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, MissingError

from odoo.addons.spreadsheet.utils.validate_data import fields_in_spreadsheet, menus_xml_ids_in_spreadsheet

class SpreadsheetMixin(models.AbstractModel):
    _name = "spreadsheet.mixin"
    _description = "Spreadsheet mixin"
    _auto = False

    spreadsheet_binary_data = fields.Binary(
        string="Spreadsheet file",
        default=lambda self: self._empty_spreadsheet_data_base64(),
    )
    spreadsheet_data = fields.Text(compute='_compute_spreadsheet_data', inverse='_inverse_spreadsheet_data')
    spreadsheet_file_name = fields.Char(compute='_compute_spreadsheet_file_name')
    thumbnail = fields.Binary()

    @api.constrains("spreadsheet_binary_data")
    def _check_spreadsheet_data(self):
        for spreadsheet in self.filtered("spreadsheet_binary_data"):
            try:
                data = json.loads(base64.b64decode(spreadsheet.spreadsheet_binary_data).decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise ValidationError(_("Uh-oh! Looks like the spreadsheet file contains invalid data."))
            if data.get("[Content_Types].xml"):
                # this is a xlsx file
                continue
            display_name = spreadsheet.display_name
            errors = []
            for model, field_chains in fields_in_spreadsheet(data).items():
                if model not in self.env:
                    errors.append(f"- model '{model}' used in '{display_name}' does not exist")
                    continue
                for field_chain in field_chains:
                    field_model = model
                    for fname in field_chain.split("."):  # field chain 'product_id.channel_ids'
                        if fname not in self.env[field_model]._fields:
                            errors.append(f"- field '{fname}' used in spreadsheet '{display_name}' does not exist on model '{field_model}'")
                            continue
                        field = self.env[field_model]._fields[fname]
                        if field.relational:
                            field_model = field.comodel_name

            for xml_id in menus_xml_ids_in_spreadsheet(data):
                record = self.env.ref(xml_id, raise_if_not_found=False)
                if not record:
                    errors.append(f"- xml id '{xml_id}' used in spreadsheet '{display_name}' does not exist")
                    continue
                # check that the menu has an action. Root menus always have an action.
                if not record.action and record.parent_id.id:
                    errors.append(f"- menu with xml id '{xml_id}' used in spreadsheet '{display_name}' does not have an action")

            if errors:
                raise ValidationError(
                    _(
                        "Uh-oh! Looks like the spreadsheet file contains invalid data.\n\n%(errors)s",
                        errors="\n".join(errors),
                    ),
                )

    @api.depends("spreadsheet_binary_data")
    def _compute_spreadsheet_data(self):
        for spreadsheet in self.with_context(bin_size=False):
            if not spreadsheet.spreadsheet_binary_data:
                spreadsheet.spreadsheet_data = False
            else:
                spreadsheet.spreadsheet_data = base64.b64decode(spreadsheet.spreadsheet_binary_data).decode()

    def _inverse_spreadsheet_data(self):
        for spreadsheet in self:
            if not spreadsheet.spreadsheet_data:
                spreadsheet.spreadsheet_binary_data = False
            else:
                spreadsheet.spreadsheet_binary_data = base64.b64encode(spreadsheet.spreadsheet_data.encode())

    @api.depends('display_name')
    def _compute_spreadsheet_file_name(self):
        for spreadsheet in self:
            spreadsheet.spreadsheet_file_name = f"{spreadsheet.display_name}.osheet.json"

    @api.onchange('spreadsheet_binary_data')
    def _onchange_data_(self):
        self._check_spreadsheet_data()

    @api.model
    def get_display_names_for_spreadsheet(self, args):
        ids_per_model = defaultdict(list)
        for arg in args:
            ids_per_model[arg["model"]].append(arg["id"])
        display_names = defaultdict(dict)
        for model, ids in ids_per_model.items():
            records = self.env[model].with_context(active_test=False).search([("id", "in", ids)])
            for record in records:
                display_names[model][record.id] = record.display_name

        # return the display names in the same order as the input
        return [
            display_names[arg["model"]].get(arg["id"])
            for arg in args
        ]

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
