import base64
import io
import json
import re
import zipfile
from collections import defaultdict

from odoo import _, api, fields, models, tools
from odoo.exceptions import MissingError, ValidationError
from odoo.libs.debug_log import DebugLog

from odoo.addons.spreadsheet.utils.validate_data import (
    fields_in_spreadsheet,
    menus_xml_ids_in_spreadsheet,
)

_debug = DebugLog(__name__)


class MixinSpreadsheet(models.AbstractModel):
    _name = "mixin.spreadsheet"
    _description = "Spreadsheet mixin"
    _auto = False

    spreadsheet_binary_data = fields.Binary(
        string="Spreadsheet file",
        default=lambda self: self._empty_spreadsheet_data_base64(),
    )
    spreadsheet_data = fields.Text(
        compute="_compute_spreadsheet_data",
        inverse="_inverse_spreadsheet_data",
    )
    spreadsheet_file_name = fields.Char(compute="_compute_spreadsheet_file_name")
    thumbnail = fields.Binary()

    @api.constrains("spreadsheet_binary_data")
    def _check_spreadsheet_data(self):
        for spreadsheet in self.filtered("spreadsheet_binary_data"):
            try:
                data = json.loads(
                    base64.b64decode(spreadsheet.spreadsheet_binary_data).decode()
                )
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                _debug.logic(
                    "spreadsheet_data_rejected",
                    records=spreadsheet,
                    reason="undecodable",
                    error=type(e).__name__,
                )
                raise ValidationError(
                    _("Uh-oh! Looks like the spreadsheet file contains invalid data.")
                ) from e
            if not (tools.config["test_enable"] or tools.config["test_file"]):
                _debug.logic(
                    "spreadsheet_data_validation_skipped",
                    records=spreadsheet,
                    reason="not_test_mode",
                )
                continue
            if data.get("[Content_Types].xml"):
                # this is a xlsx file
                _debug.logic(
                    "spreadsheet_data_validation_skipped",
                    records=spreadsheet,
                    reason="xlsx",
                )
                continue
            display_name = spreadsheet.display_name
            errors = []
            fields_by_model = fields_in_spreadsheet(data)
            menu_xml_ids = menus_xml_ids_in_spreadsheet(data)
            _debug.pipeline(
                "spreadsheet_data_references_extracted",
                records=spreadsheet,
                models=len(fields_by_model),
                field_chains=sum(len(chains) for chains in fields_by_model.values()),
                menus=len(menu_xml_ids),
            )
            for model, field_chains in fields_by_model.items():
                if model not in self.env:
                    errors.append(
                        f"- model '{model}' used in '{display_name}' does not exist"
                    )
                    continue
                for field_chain in field_chains:
                    field_model = model
                    for fname in field_chain.split(
                        "."
                    ):  # field chain 'product_id.channel_ids'
                        if fname not in self.env[field_model]._fields:
                            errors.append(
                                f"- field '{fname}' used in spreadsheet '{display_name}' does not exist on model '{field_model}'"
                            )
                            break
                        field = self.env[field_model]._fields[fname]
                        if field.relational:
                            field_model = field.comodel_name

            for xml_id in menu_xml_ids:
                record = self.env.ref(xml_id, raise_if_not_found=False)
                if not record:
                    errors.append(
                        f"- xml id '{xml_id}' used in spreadsheet '{display_name}' does not exist"
                    )
                    continue
                # check that the menu has an action. Root menus always have an action.
                if not record.action and record.parent_id.id:
                    errors.append(
                        f"- menu with xml id '{xml_id}' used in spreadsheet '{display_name}' does not have an action"
                    )

            if errors:
                _debug.logic(
                    "spreadsheet_data_rejected",
                    records=spreadsheet,
                    reason="dangling_references",
                    errors=len(errors),
                )
                raise ValidationError(
                    _(
                        "Uh-oh! Looks like the spreadsheet file contains invalid data.\n\n%(errors)s",
                        errors="\n".join(errors),
                    ),
                )

    @api.depends("spreadsheet_binary_data")
    def _compute_spreadsheet_data(self):
        attachments = (
            self.env["ir.attachment"]
            .with_context(bin_size=False)
            .search(
                [
                    ("res_model", "=", self._name),
                    ("res_field", "=", "spreadsheet_binary_data"),
                    ("res_id", "in", self.ids),
                ]
            )
        )
        _debug.perf.count(
            "spreadsheet_data_attachments_fetched",
            records=self,
            rows=len(attachments),
        )
        data = {attachment.res_id: attachment.raw for attachment in attachments}
        for spreadsheet in self:
            spreadsheet.spreadsheet_data = data.get(spreadsheet.id, False)

    def _inverse_spreadsheet_data(self):
        for spreadsheet in self:
            if not spreadsheet.spreadsheet_data:
                spreadsheet.spreadsheet_binary_data = False
            else:
                spreadsheet.spreadsheet_binary_data = base64.b64encode(
                    spreadsheet.spreadsheet_data.encode()
                )

    @api.depends("display_name")
    def _compute_spreadsheet_file_name(self):
        for spreadsheet in self:
            spreadsheet.spreadsheet_file_name = (
                f"{spreadsheet.display_name}.osheet.json"
            )

    @api.onchange("spreadsheet_binary_data")
    def _onchange_data_(self):
        self._check_spreadsheet_data()

    @api.readonly
    @api.model
    def get_display_names_for_spreadsheet(self, args):
        ids_per_model = defaultdict(list)
        for arg in args:
            ids_per_model[arg["model"]].append(arg["id"])
        display_names = defaultdict(dict)
        for model, ids in ids_per_model.items():
            Model = self.env.get(model)
            if Model is None:
                _debug.logic(
                    "spreadsheet_display_names_model_missing", model=model, ids=len(ids)
                )
                continue
            records = Model.with_context(active_test=False).search([("id", "in", ids)])  # noqa: E8507 - one query per model
            for record in records:
                display_names[model][record.id] = record.display_name

        _debug.pipeline(
            "spreadsheet_display_names_resolved",
            requested=len(args),
            models=len(ids_per_model),
            resolved=sum(len(names) for names in display_names.values()),
        )
        # return the display names in the same order as the input
        return [display_names[arg["model"]].get(arg["id"]) for arg in args]

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
        lang = self.env["res.lang"]._get_lang_cached(self.env.user.lang)
        locale = lang._odoo_lang_to_spreadsheet_locale()
        return {
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
        with (
            _debug.perf("spreadsheet_xlsx_zipped", files=len(files)) as span,
            zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as doc_zip,
        ):
            images = missing_images = 0
            for f in files:
                # to reduce networking load, only the image path is sent.
                # It's replaced by the image content here.
                if "imageSrc" in f:
                    images += 1
                    try:
                        content = self._get_file_content(f["imageSrc"])
                        doc_zip.writestr(f["path"], content)
                    except MissingError:
                        missing_images += 1
                        _debug.logic("spreadsheet_xlsx_image_missing", path=f["path"])
                else:
                    doc_zip.writestr(f["path"], f["content"])
            span.set(images=images, missing_images=missing_images)

        return stream.getvalue()

    def _get_file_content(self, file_path):
        if file_path.startswith("data:image/png;base64,"):
            _debug.logic("spreadsheet_file_content_source", source="data_uri")
            return base64.b64decode(file_path.split(",")[1])
        match = re.match(r"/web/image/(\d+)", file_path)
        if not match:
            _debug.logic(
                "spreadsheet_file_content_rejected",
                reason="invalid_path",
                path=file_path,
            )
            raise ValidationError(
                _("Invalid image path: %(file_path)s", file_path=file_path)
            )
        _debug.logic(
            "spreadsheet_file_content_source",
            source="attachment",
            attachment_id=match.group(1),
        )
        file_record = self.env["ir.binary"]._get_record(
            res_model="ir.attachment",
            res_id=int(match.group(1)),
        )
        return self.env["ir.binary"]._get_stream_from_record(file_record).read()
