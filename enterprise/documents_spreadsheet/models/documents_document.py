# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import contextlib
import io
import json
import zipfile

from lxml import etree

from odoo import _, Command, fields, models, api
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.osv import expression
from odoo.tools import format_list, image_process, consteq
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT


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
    spreadsheet_thumbnail_checksum = fields.Char(
        compute='_compute_spreadsheet_thumbnail_checksum',
        export_string_translation=False
    )
    excel_export = fields.Binary()

    handler = fields.Selection([
        ("spreadsheet", "Spreadsheet"),
        ("frozen_folder", "Frozen Folder"),
        ("frozen_spreadsheet", "Frozen Spreadsheet"),
    ], ondelete={"spreadsheet": "cascade", "frozen_folder": "cascade", "frozen_spreadsheet": "cascade"})

    _sql_constraints = [(
        'spreadsheet_access_via_link',
        "CHECK((handler != 'spreadsheet') OR access_via_link != 'edit')",
        "To share a spreadsheet in edit mode, add the user in the accesses"
    ), (
        'frozen_spreadsheet_access_via_link_access_internal',
        "CHECK((handler != 'frozen_spreadsheet') OR (access_via_link != 'edit' AND access_internal != 'edit'))",
        "A frozen spreadsheet can not be editable"
    )]

    @api.returns('documents.document', lambda d: {'id': d.id, 'shortcut_document_id': d.shortcut_document_id.id})
    def action_freeze_and_copy(self, spreadsheet_data, excel_files):
        """Render the spreadsheet in JS, and then make a copy to share it.

        :param spreadsheet_data: The spreadsheet data to save
        :param excel_files: The files to download
        """
        self.ensure_one()

        # we will copy in SUDO to skip check on frozen spreadsheets
        # (see @_check_spreadsheet_share)
        self.env['documents.document'].check_access('create')
        self.check_access('read')
        if not self.env.su and self.folder_id and self.folder_id.user_permission != 'edit':
            raise AccessError(_('You are not allowed to freeze spreadsheets in Company'))

        folder_sudo = self.env['documents.document'].sudo().search([
            ('folder_id', '=', self.folder_id.id),
            ('type', '=', 'folder'),
            ('handler', '=', 'frozen_folder'),
        ], limit=1)

        if not folder_sudo:
            folder_sudo = self.env['documents.document'].sudo().create({
                'name': _('Frozen spreadsheets'),
                'type': 'folder',
                'handler': 'frozen_folder',
                'folder_id': self.folder_id.id,
                'access_via_link': 'none',
                'access_internal': 'none',
                'access_ids': False,
                'owner_id': self.env.ref('base.user_root').id,
            })

        if isinstance(spreadsheet_data, dict):
            spreadsheet_data = json.dumps(spreadsheet_data)

        return self.sudo().copy({
            'name': _('Frozen at %(date)s: %(name)s',
                      date=fields.Date.today().strftime(DEFAULT_SERVER_DATE_FORMAT), name=self.name),
            'access_internal': 'none' if self.access_internal == 'none' else 'view',
            'access_via_link': 'view',
            'spreadsheet_data': spreadsheet_data,
            'folder_id': folder_sudo.id,
            'excel_export': base64.b64encode(self.env['spreadsheet.mixin']._zip_xslx_files(excel_files)),
            'handler': 'frozen_spreadsheet',
            'is_access_via_link_hidden': True,
            'access_ids': [Command.create({
                'partner_id': access.partner_id.id,
                'role': 'view' if access.role == 'edit' else access.role,
            }) for access in self.access_ids if access.role],
        })

    def _get_access_update_domain(self):
        """Allow to change the access of the frozen folders / spreadsheets only if we open their share panel."""
        return expression.AND([
            super()._get_access_update_domain(),
            expression.OR([
                [('id', 'in', self.ids)],
                [('handler', 'not in', ('frozen_folder', 'frozen_spreadsheet'))],
            ]),
        ])

    @api.constrains('company_id')
    def _check_company_id(self):
        domain = expression.OR([
            [('document_spreadsheet_folder_id', '=', folder.id), ('id', '!=', folder.company_id.id)]
            for folder in self
            if folder.company_id and folder.type == 'folder'
        ])
        companies = self.env['res.company'].search(domain)
        if companies:
            errors = format_list(self.env, [
                self.env._("%(folder)s is used by %(company)s", folder=comp.document_spreadsheet_folder_id.display_name, company=comp.display_name)
                for comp in companies
            ])
            raise ValidationError(_("The company for a folder cannot be changed if it is already used as the "
                                    "spreadsheet workspace for at least one other company: %s", errors))

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = self._assign_spreadsheet_default_values(vals_list)
        vals_list = self._resize_spreadsheet_thumbnails(vals_list)
        documents = super().create(vals_list)
        documents._update_spreadsheet_contributors()
        return documents

    def write(self, vals):
        if 'handler' not in vals and 'mimetype' in vals and vals['mimetype'] != 'application/o-spreadsheet':
            vals['handler'] = False
        if 'spreadsheet_data' in vals:
            self._update_spreadsheet_contributors()
        if all(document.handler in ("spreadsheet", "frozen_spreadsheet") for document in self):
            vals = self._resize_thumbnail_value(vals)
        return super().write(vals)

    def dispatch_spreadsheet_message(self, message, access_token=None):
        if self.sudo().handler == "frozen_spreadsheet":
            return False
        return super().dispatch_spreadsheet_message(message, access_token)

    def join_spreadsheet_session(self, access_token=None):
        if self.sudo().handler not in ("spreadsheet", "frozen_spreadsheet"):
            raise ValidationError(_("The spreadsheet you are trying to access does not exist."))
        data = super().join_spreadsheet_session(access_token)
        self._update_spreadsheet_contributors()
        sudo_self = self.sudo()
        return {
            **data,
            'handler': sudo_self.handler,
            'access_url': sudo_self.access_url,
            'is_favorited': sudo_self.is_favorited,
            'folder_id': sudo_self.folder_id.id,
            'copy_in_my_drive': self._cannot_create_sibling(),
        }

    @api.constrains('owner_id')
    def _check_owner_is_internal_user(self):
        spreadsheet_docs = self.filtered(lambda rec: rec.handler in ("spreadsheet", "frozen_spreadsheet"))
        if any(user.share for user in spreadsheet_docs.owner_id):
            raise AccessError(_("Portal users cannot be the owner of a spreadsheet."))

    def _check_spreadsheet_share(self, operation, access_token):
        if not self.env.su and operation == 'write' and self.sudo().handler == 'frozen_spreadsheet':
            raise AccessError(_("You can not edit a frozen spreadsheet"))

        with contextlib.suppress(AccessError):
            super()._check_spreadsheet_share(operation, access_token)
            return

        if (
            not access_token
            or not consteq(access_token, self.sudo().access_token)
            or (operation == 'write' and self.sudo().access_via_link != 'edit')
            or (operation == 'read' and self.sudo().access_via_link == 'none')
        ):
            raise AccessError(_("You don't have access to this document"))

    def _compute_file_extension(self):
        """ Spreadsheet documents do not have file extension. """
        spreadsheet_docs = self.filtered(lambda rec: rec.handler in ("spreadsheet", "frozen_spreadsheet"))
        spreadsheet_docs.file_extension = False
        super(Document, self - spreadsheet_docs)._compute_file_extension()

    @api.depends("attachment_id", "handler")
    def _compute_spreadsheet_data(self):
        for document in self.with_context(bin_size=False):
            if document.handler in ("spreadsheet", "frozen_spreadsheet"):
                document.spreadsheet_data = document.attachment_id.raw
            else:
                document.spreadsheet_data = False

    @api.depends("datas", "handler")
    def _compute_spreadsheet_binary_data(self):
        for document in self:
            if document.handler in ("spreadsheet", "frozen_spreadsheet"):
                document.spreadsheet_binary_data = document.datas
            else:
                document.spreadsheet_binary_data = False

    def _inverse_spreadsheet_binary_data(self):
        for document in self:
            if document.handler in ("spreadsheet", "frozen_spreadsheet"):
                document.write({
                    "datas": document.spreadsheet_binary_data,
                    "mimetype": "application/o-spreadsheet"
                })

    @api.depends_context('uid')
    @api.depends("display_thumbnail")
    def _compute_spreadsheet_thumbnail_checksum(self):
        spreadsheets = self.filtered(lambda doc: doc.handler == "spreadsheet")
        thumbnails = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', self._name),
            ('res_field', '=', 'display_thumbnail'),
            ('res_id', 'in', spreadsheets.ids),
            ('create_uid', '=', self.env.uid)
        ])
        thumbnails_by_documents = thumbnails.grouped("res_id")
        for document in self:
            thumbnail = thumbnails_by_documents.get(document.id)
            if thumbnail:
                document.spreadsheet_thumbnail_checksum = thumbnail.checksum
            else:
                document.spreadsheet_thumbnail_checksum = False

    @api.depends("checksum", "handler")
    def _compute_thumbnail(self):
        # Spreadsheet thumbnails cannot be computed from their binary data.
        # They should be saved independently.
        spreadsheets = self.filtered(lambda d: d.handler in ("spreadsheet", "frozen_spreadsheet"))
        super(Document, self - spreadsheets)._compute_thumbnail()

    def _copy_spreadsheet_image_attachments(self):
        spreadsheets = self.filtered(lambda d: d.handler in ("spreadsheet", "frozen_spreadsheet"))
        super(Document, spreadsheets)._copy_spreadsheet_image_attachments()

    def _copy_attachment_filter(self, default):
        return super()._copy_attachment_filter(default).filtered(
            lambda d: d.handler not in ("spreadsheet", "frozen_spreadsheet"))

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
                if vals.get('handler') in ('spreadsheet', 'frozen_spreadsheet')
                else vals
            )
            for vals in vals_list
        ]

    def _assign_spreadsheet_default_values(self, vals_list):
        """Make sure spreadsheet values have a `folder_id`. Assign the
        default spreadsheet folder if there is none.
        """
        # Use the current company's spreadsheet workspace, since `company_id` on `documents.document` is a related field
        # on `folder_id` we do not need to check vals_list for different companies.
        default_folder = self.env.company.document_spreadsheet_folder_id
        if not default_folder:
            default_folder = self.env['documents.document'].search([], limit=1)
        return [
            {
                'folder_id': default_folder.id,
                **vals,
            }
            if vals.get('handler') == 'spreadsheet' else vals
            for vals in vals_list
        ]

    def _update_spreadsheet_contributors(self):
        """Add the current user to the spreadsheet contributors.
        """
        can_write = self.env['spreadsheet.contributor'].has_access('write')
        can_create = self.env['spreadsheet.contributor'].has_access('create')
        if not can_write or not can_create:
            return
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
        action_open = spreadsheet.action_open_spreadsheet()
        action_open['params']['is_new_spreadsheet'] = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'message': self._creation_msg(),
                'next': action_open
            }
        }

    @api.model
    def _get_spreadsheets_to_display(self, domain, offset=0, limit=None):
        """
        Get all the spreadsheets, with the spreadsheet that the user has recently
        opened at first.
        """
        # TODO: improve with _read_group to not fetch all records
        Contrib = self.env["spreadsheet.contributor"]
        visible_docs = self.search(expression.AND([domain, [("handler", "in", ("spreadsheet", "frozen_spreadsheet"))]]))
        contribs = Contrib.search(
            [
                ("document_id", "in", visible_docs.ids),
                ("user_id", "=", self.env.user.id),
            ],
            order="last_update_date DESC, id DESC",
        )
        user_docs = contribs.document_id
        # Intersection is used to apply the `domain` to `user_doc`, the union is
        # here to keep only the visible docs, but with the order of contribs.
        docs = ((user_docs & visible_docs) | visible_docs)
        if limit:
            docs = docs[offset:offset + limit]
        else:
            docs = docs[offset:]
        return docs.read(["display_name", "display_thumbnail"])

    @api.model
    def _get_shortcuts_copy_fields(self):
        return super()._get_shortcuts_copy_fields() | {'handler'}

    def clone_xlsx_into_spreadsheet(self, archive_source=False):
        """Clone an XLSX document into a new document with its content unzipped, and return the new document id"""
        self.ensure_one()

        unzipped, attachments = self._unzip_xlsx()

        def adjust_role(partner, role):
            """Ensure non-internal users do not have 'edit' access."""
            user_ids = partner.with_context(active_test=False).user_ids
            return 'view' if not user_ids or all(user_ids.mapped("share")) else role

        access_ids = [
            Command.create({
                'partner_id': acc.partner_id.id,
                'role': adjust_role(acc.partner_id, acc.role)
            })
            for acc in self.access_ids.filtered("role")
        ]

        doc = self.copy({
            "access_ids": access_ids,
            "attachment_id": False,
            "handler": "spreadsheet",
            "mimetype": "application/o-spreadsheet",
            "name": self.name.rstrip(".xlsx"),
            "spreadsheet_data": json.dumps(unzipped),
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

        if self.mimetype in XLSX_MIME_TYPES and self.attachment_id.raw:
            file = io.BytesIO(self.attachment_id.raw)
            if not zipfile.is_zipfile(file):
                return None
            with zipfile.ZipFile(file) as archive:
                if '[Content_Types].xml' not in archive.namelist():
                    # the xlsx file is invalid
                    return None
                with archive.open("[Content_Types].xml") as myfile:
                    content = myfile.read()
                    tree = etree.fromstring(content)
                    nodes = tree.xpath(
                        "//ns:Override[@ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml']",
                        namespaces={"ns": "http://schemas.openxmlformats.org/package/2006/content-types"}
                    )
                    return len(nodes) > 1

        if self.handler in ("spreadsheet", "frozen_spreadsheet"):
            spreadsheet_data = json.loads(self.spreadsheet_data or '{}')
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
            raise UserError(_("The file is not a xlsx file"))

        unzipped_size = 0
        with zipfile.ZipFile(file) as input_zip:
            if len(input_zip.infolist()) > 1000:
                raise UserError(_("The xlsx file is too big"))

            if "[Content_Types].xml" not in input_zip.namelist() or \
                    not any(name.startswith("xl/") for name in input_zip.namelist()):
                raise UserError(_("The xlsx file is corrupted"))

            unzipped = {}
            attachments = []
            for info in input_zip.infolist():
                if not (info.filename.endswith((".xml", ".xml.rels")) or "media/image" in info.filename) or\
                        not info.filename.startswith(SUPPORTED_PATHS):
                    # Don't extract files others than xmls or unsupported xmls
                    continue

                unzipped_size += info.file_size
                if unzipped_size > 50 * 1000 * 1000:  # 50MB
                    raise UserError(_("The xlsx file is too big"))

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
        """TODO: remove in master"""

    def action_open_spreadsheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'action_open_spreadsheet',
            'params': {
                'spreadsheet_id': self.id,
            }
        }

    @api.model
    def get_spreadsheets(self, domain=(), offset=0, limit=None):
        domain = expression.AND([domain, [("handler", "=", "spreadsheet")]])
        return {
            "records": self._get_spreadsheets_to_display(domain, offset, limit),
            "total": self.search_count(domain),
        }

    def _creation_msg(self):
        return (
            _("New spreadsheet created in My Drive")
            if not self.folder_id and self.owner_id == self.env.user
            else  _("New spreadsheet created in Documents")
        )

    @api.model
    def _get_spreadsheet_selector(self):
        return {
            "model": self._name,
            "display_name": _("Spreadsheets"),
            "sequence": 0,
            "allow_create": True,
        }

    def _permission_specification(self):
        specification = super()._permission_specification()
        specification['handler'] = {}
        if self.env.user.has_group('base.group_user'):
            specification['access_ids']['fields']['partner_id']['fields']['partner_share'] = {}
        return specification

    def _contains_live_data(self):
        """Return true if the spreadsheet contains live data, like Odoo pivots, chart, etc."""
        self.ensure_one()
        if self.handler != 'spreadsheet':
            return False

        snapshot = self._get_spreadsheet_snapshot()
        if snapshot.get("lists") or snapshot.get("pivots") or snapshot.get("chartOdooMenusReferences"):
            return True

        for sheet in snapshot.get("sheets", []):
            for figure in sheet.get("figures", []):
                if figure.get("data", {}).get("type", "").startswith("odoo_"):
                    return True

        revisions = self._build_spreadsheet_messages()
        return any(
            command.get("type") in ("INSERT_ODOO_LIST", "ADD_PIVOT", "LINK_ODOO_MENU_TO_CHART")
            or (
                command.get("type") == "CREATE_CHART"
                and command.get("definition", {}).get("type", "").startswith("odoo_")
            )
            for revision in revisions
            for command in revision.get("commands", [])
        )

    def _get_writable_record_name_field(self):
        return 'name'
