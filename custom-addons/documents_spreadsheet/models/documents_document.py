# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import json
import zipfile
import datetime

from lxml import etree

from odoo import _, fields, models, api
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.osv import expression
from odoo.tools import image_process


SUPPORTED_PATHS = (
    "[Content_Types].xml",
    "xl/sharedStrings.xml",
    "xl/styles.xml",
    "xl/workbook.xml",
    "_rels/",
    "xl/_rels",
    "xl/charts/",
    "xl/drawings/",
    "xl/externalLinks/",
    "xl/pivotTables/",
    "xl/tables/",
    "xl/theme/",
    "xl/worksheets/",
    "xl/media",
)

XLSX_MIME_TYPES = [
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/wps-office.xlsx",
]


class Document(models.Model):
    _name = "documents.document"
    _inherit = ["documents.document", "spreadsheet.mixin"]

    spreadsheet_binary_data = fields.Binary(compute='_compute_spreadsheet_binary_data', inverse='_inverse_spreadsheet_binary_data', default=None)

    handler = fields.Selection(
        [("spreadsheet", "Spreadsheet")], ondelete={"spreadsheet": "cascade"}
    )

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = self._assign_spreadsheet_default_folder(vals_list)
        vals_list = self._resize_spreadsheet_thumbnails(vals_list)
        documents = super().create(vals_list)
        documents._update_spreadsheet_contributors()
        return documents

    def write(self, vals):
        if 'handler' not in vals and 'mimetype' in vals and vals['mimetype'] != 'application/o-spreadsheet':
            vals['handler'] = False
        if 'spreadsheet_data' in vals:
            self._update_spreadsheet_contributors()
        if all(document.handler == 'spreadsheet' for document in self):
            vals = self._resize_thumbnail_value(vals)
        return super().write(vals)

    def join_spreadsheet_session(self, share_id=None, access_token=None):
        if self.sudo().handler != "spreadsheet":
            raise ValidationError(_("The spreadsheet you are trying to access does not exist."))
        data = super().join_spreadsheet_session(share_id, access_token)
        self._update_spreadsheet_contributors()
        return dict(data, is_favorited=self.sudo().is_favorited, folder_id=self.sudo().folder_id.id)

    def _check_spreadsheet_share(self, operation, share_id, access_token):
        share = self.env['documents.share'].browse(share_id).sudo()
        available_documents = share._get_documents_and_check_access(access_token, operation=operation)
        if not available_documents or self not in available_documents:
            raise AccessError(_("You don't have access to this document"))

    def _compute_file_extension(self):
        """ Spreadsheet documents do not have file extension. """
        spreadsheet_docs = self.filtered(lambda rec: rec.handler == "spreadsheet")
        spreadsheet_docs.file_extension = False
        super(Document, self - spreadsheet_docs)._compute_file_extension()

    @api.depends("datas", "handler")
    def _compute_spreadsheet_binary_data(self):
        for document in self:
            if document.handler == "spreadsheet":
                document.spreadsheet_binary_data = document.datas
            else:
                document.spreadsheet_binary_data = False

    def _inverse_spreadsheet_binary_data(self):
        for document in self:
            if document.handler == "spreadsheet":
                document.write({
                    "datas": document.spreadsheet_binary_data,
                    "mimetype": "application/o-spreadsheet"
                })

    @api.depends("checksum", "handler")
    def _compute_thumbnail(self):
        # Spreadsheet thumbnails cannot be computed from their binary data.
        # They should be saved independently.
        spreadsheets = self.filtered(lambda d: d.handler == "spreadsheet")
        super(Document, self - spreadsheets)._compute_thumbnail()

    def _copy_spreadsheet_image_attachments(self):
        if self.handler != "spreadsheet":
            return
        super()._copy_spreadsheet_image_attachments()

    def _resize_thumbnail_value(self, vals):
        if 'thumbnail' in vals:
            return dict(
                vals,
                thumbnail=base64.b64encode(image_process(base64.b64decode(vals['thumbnail'] or ''), size=(750, 750), crop='center')),
            )
        return vals

    def _resize_spreadsheet_thumbnails(self, vals_list):
        return [
            (
                self._resize_thumbnail_value(vals)
                if vals.get('handler') == 'spreadsheet'
                else vals
            )
            for vals in vals_list
        ]

    def _assign_spreadsheet_default_folder(self, vals_list):
        """Make sure spreadsheet values have a `folder_id`. Assign the
        default spreadsheet folder if there is none.
        """
        # Use the current company's spreadsheet workspace, since `company_id` on `documents.document` is a related field
        # on `folder_id` we do not need to check vals_list for different companies.
        default_folder = self.env.company.documents_spreadsheet_folder_id
        if not default_folder:
            default_folder = self.env['documents.folder'].search([], limit=1, order="sequence asc")
        return [
            (
                dict(vals, folder_id=vals.get('folder_id', default_folder.id))
                if vals.get('handler') == 'spreadsheet'
                else vals
            )
            for vals in vals_list
        ]

    def _update_spreadsheet_contributors(self):
        """Add the current user to the spreadsheet contributors.
        """
        for document in self:
            if document.handler == 'spreadsheet':
                self.env['spreadsheet.contributor']._update(self.env.user, document)

    @api.model
    def action_open_new_spreadsheet(self, vals=None):
        if vals is None:
            vals = {}
        spreadsheet = self.create({
            "name": _("Untitled spreadsheet"),
            "mimetype": "application/o-spreadsheet",
            "datas": self._empty_spreadsheet_data_base64(),
            "handler": "spreadsheet",
            **vals,
        })
        return {
            "type": "ir.actions.client",
            "tag": "action_open_spreadsheet",
            "params": {
                "spreadsheet_id": spreadsheet.id,
                "is_new_spreadsheet": True,
            },
        }

    @api.model
    def get_spreadsheets_to_display(self, domain, offset=0, limit=None):
        """
        Get all the spreadsheets, with the spreadsheet that the user has recently
        opened at first.
        """
        Contrib = self.env["spreadsheet.contributor"]
        visible_docs = self.search(expression.AND([domain, [("handler", "=", "spreadsheet")]]))
        contribs = Contrib.search(
            [
                ("document_id", "in", visible_docs.ids),
                ("user_id", "=", self.env.user.id),
            ],
            order="last_update_date desc",
        )
        user_docs = contribs.document_id
        # Intersection is used to apply the `domain` to `user_doc`, the union is
        # here to keep only the visible docs, but with the order of contribs.
        docs = ((user_docs & visible_docs) | visible_docs)
        if (limit):
            docs = docs[offset:offset + limit]
        else:
            docs = docs[offset:]
        return docs.read(["name", "thumbnail"])

    def clone_xlsx_into_spreadsheet(self, archive_source=False):
        """Clone an XLSX document into a new document with its content unzipped, and return the new document id"""

        self.ensure_one()

        unzipped, attachments = self._unzip_xlsx()

        doc = self.copy({
            "handler": "spreadsheet",
            "mimetype": "application/o-spreadsheet",
            "name": self.name.rstrip(".xlsx"),
            "spreadsheet_data": json.dumps(unzipped)
        })

        for attachment in attachments:
            attachment.write({'res_id': doc.id})

        if archive_source:
            self.action_archive()

        return doc.id

    def _get_is_multipage(self):
        """Override for spreadsheets and xlsx."""
        is_multipage = super()._get_is_multipage()
        if is_multipage is not None:
            return is_multipage

        if self.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" and self.attachment_id.raw:
            try:
                spreadsheet_data = self._unzip_xlsx()[0]
            except XSLXReadUserError:
                # No need to raise for this, just return that we don't know
                return None
            return self._is_xlsx_data_multipage(spreadsheet_data)

        if self.handler == "spreadsheet":
            spreadsheet_data = json.loads(self.spreadsheet_data)
            if spreadsheet_data.get("sheets"):
                return len(spreadsheet_data["sheets"]) > 1
            return self._is_xlsx_data_multipage(spreadsheet_data)

    @api.model
    def _is_xlsx_data_multipage(self, spreadsheet_data):
        for filename, content in spreadsheet_data.items():
            if filename.endswith("workbook.xml.rels"):
                tree = etree.fromstring(content.encode())
                nodes = tree.findall(
                    './/rels:Relationship',
                    {'rels': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                )
                found_first_sheet = False
                for node in nodes:
                    if node.attrib["Type"].endswith('/relationships/worksheet'):
                        if found_first_sheet:
                            return True
                        found_first_sheet = True
                break

        return False

    def _unzip_xlsx(self):
        file = io.BytesIO(self.attachment_id.raw)
        if not zipfile.is_zipfile(file) or self.mimetype not in XLSX_MIME_TYPES:
            raise XSLXReadUserError(_("The file is not a xlsx file"))

        unzipped_size = 0
        with zipfile.ZipFile(file) as input_zip:
            if len(input_zip.infolist()) > 1000:
                raise XSLXReadUserError(_("The xlsx file is too big"))

            if "[Content_Types].xml" not in input_zip.namelist() or \
                    not any(name.startswith("xl/") for name in input_zip.namelist()):
                raise XSLXReadUserError(_("The xlsx file is corrupted"))

            unzipped = {}
            attachments = []
            for info in input_zip.infolist():
                if not (info.filename.endswith((".xml", ".xml.rels")) or "media/image" in info.filename) or\
                        not info.filename.startswith(SUPPORTED_PATHS):
                    # Don't extract files others than xmls or unsupported xmls
                    continue

                unzipped_size += info.file_size
                if unzipped_size > 50 * 1000 * 1000:  # 50MB
                    raise XSLXReadUserError(_("The xlsx file is too big"))

                if info.filename.endswith((".xml", ".xml.rels")):
                    unzipped[info.filename] = input_zip.read(info.filename).decode()
                elif "media/image" in info.filename:
                    image_file = input_zip.read(info.filename)
                    attachment = self._upload_image_file(image_file, info.filename)
                    attachments.append(attachment)
                    unzipped[info.filename] = {
                        "imageSrc": "/web/image/" + str(attachment.id),
                    }
        return unzipped, attachments

    def _upload_image_file(self, image_file, filename):
        attachment_model = self.env['ir.attachment']
        attachment = attachment_model.create({
            'name': filename,
            'datas': base64.encodebytes(image_file),
            'res_model': "documents.document",
        })
        attachment._post_add_create()
        return attachment

    @api.autovacuum
    def _gc_spreadsheet(self):
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        domain = [
            ('handler', '=', 'spreadsheet'),
            ('create_date', '<', yesterday),
            ('spreadsheet_revision_ids', '=', False),
            ('spreadsheet_snapshot', '=', False)
        ]
        self.search(domain).action_archive()

    def action_edit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'action_open_spreadsheet',
            'params': {
                'spreadsheet_id': self.id,
            }
        }

    def _creation_msg(self):
        return _("New spreadsheet created in Documents")

class XSLXReadUserError(UserError):
    pass
