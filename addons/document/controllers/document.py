import base64
import io
import json
import logging
import pathlib
import zipfile
from collections import defaultdict
from contextlib import ExitStack
from http import HTTPStatus
from typing import Any, NamedTuple
from urllib.parse import quote, urlparse

from werkzeug.exceptions import BadRequest, Forbidden, RequestEntityTooLarge

from odoo import SUPERUSER_ID, Command, _, fields, http
from odoo.exceptions import MissingError
from odoo.fields import Domain
from odoo.http import prepare_content_disposition_header, request
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, consteq, replace_exceptions, str2bool
from odoo.tools.image import base64_to_image
from odoo.tools.urls import keep_query

from odoo.addons.document.tools import (
    UserFolder,
    is_mimetype_textual,
)
from odoo.addons.mail.controllers.attachment import AttachmentController

logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_SAFE_REDIRECT_SCHEMES = frozenset({"http", "https", "ftp", "ftps", "mailto"})


def _is_safe_redirect_url(url: str) -> bool:
    if not url:
        return False
    scheme = urlparse(url).scheme.lower()
    return not scheme or scheme in _SAFE_REDIRECT_SCHEMES


_ZIP_READ_BLOCK = 256 * 1024


class ZipEntry(NamedTuple):
    path: str
    stream: Any | None
    document: Any = None
    reader: Any = None


class _ZipSink:
    __slots__ = ("_chunks",)

    def __init__(self) -> None:
        self._chunks = []

    def write(self, data: bytes) -> int:
        self._chunks.append(bytes(data))
        return len(data)

    def flush(self) -> None:
        pass

    def take(self) -> bytes:
        chunks, self._chunks = self._chunks, []
        return b"".join(chunks)


def _read_stream_blocks(stream: Any, reader: Any = None) -> Any:
    if reader is not None:
        yield from reader(_ZIP_READ_BLOCK)
        return
    if stream.type == "path":
        with open(stream.path, "rb") as source:  # noqa: PTH123 — plain fs path
            while block := source.read(_ZIP_READ_BLOCK):
                yield block
    else:
        content = stream.read()
        for offset in range(0, len(content), _ZIP_READ_BLOCK):
            yield content[offset : offset + _ZIP_READ_BLOCK]


def _normalize_zip_name(name: str) -> str:
    name = (name or "").replace("/", "_").replace("\\", "_")
    if name in (".", ".."):
        name = "_" * len(name)
    return name


class ShareRoute(http.Controller):
    TEXTUAL_THUMBNAIL_SIZE = 4096
    ZIP_MAX_FILE_COUNT = 10000
    ZIP_MAX_TOTAL_SIZE = 1024 * 1024 * 1024

    def _max_content_length(self) -> int:
        return request.env["document.document"].get_document_max_upload_limit()

    @classmethod
    def _is_shortcut_target_reachable(cls, document_sudo: Any) -> bool:
        target_sudo = document_sudo.shortcut_document_id
        if not target_sudo:
            return True
        if request.env.user._is_public():
            return (
                target_sudo.access_via_link in ("view", "edit")
                and not target_sudo.is_access_via_link_hidden
            )
        return target_sudo.user_permission != "none"

    @classmethod
    def _folder_children_domain(cls) -> Any:
        link_target_domain = Domain("access_via_link", "in", ("view", "edit")) & Domain(
            "is_access_via_link_hidden", "=", False
        )
        if not request.env.user._is_public():
            link_target_domain |= Domain("user_permission", "!=", "none")
        reachable_target_domain = Domain(
            "shortcut_document_id", "any", link_target_domain
        )
        shortcut_domain = Domain("shortcut_document_id", "=", False) | (
            reachable_target_domain
        )

        permission_domain = Domain.AND(
            [
                [("is_access_via_link_hidden", "=", False)],
                [("access_via_link", "in", ("edit", "view"))],
                Domain.OR(
                    [
                        [("access_via_link", "=", "edit")],
                        [("type", "!=", "binary")],
                        Domain.OR(
                            [
                                [("attachment_id", "!=", False)],
                                [
                                    (
                                        "shortcut_document_id.attachment_id",
                                        "!=",
                                        False,
                                    )
                                ],
                            ]
                        ),
                    ]
                ),
            ]
        )
        if not request.env.user._is_public():
            permission_domain |= Domain("user_permission", "!=", "none")

        return permission_domain & shortcut_domain

    @classmethod
    def _get_folder_children(cls, folder_sudo: Any) -> Any:
        return (
            request.env["document.document"]
            .sudo()
            .search(
                Domain("folder_id", "=", folder_sudo.id)
                & cls._folder_children_domain(),
                order="name",
            )
        )

    @classmethod
    def _get_folders_children(cls, folders_sudo: Any) -> dict:
        empty = request.env["document.document"].sudo()
        result = dict.fromkeys(folders_sudo.ids, empty)
        if not folders_sudo:
            return result
        children = empty.search(
            Domain("folder_id", "in", folders_sudo.ids) & cls._folder_children_domain(),
            order="name",
        )
        for folder, folder_children in children.grouped(
            lambda child: child.folder_id.id
        ).items():
            result[folder] = folder_children
        return result

    @staticmethod
    def _split_access_token(access_token: str) -> tuple[str, int]:
        try:
            document_token, __, encoded_id = (access_token or "").rpartition("o")
            document_id = int(encoded_id, 16)
        except ValueError:
            return "", 0
        if not document_token or document_id < 1:
            return "", 0
        return document_token, document_id

    @classmethod
    def _from_access_token(
        cls, access_token: str, *, skip_log: bool = False, follow_shortcut: bool = True
    ) -> Any:
        Doc = request.env["document.document"]

        document_token, document_id = cls._split_access_token(access_token)
        if not document_id:
            _debug.logic("token_refused", reason="malformed")
            return Doc
        document_sudo = Doc.browse(document_id).sudo()
        try:
            if not document_sudo.document_token:
                _debug.logic("token_refused", reason="no_token", document=document_id)
                return Doc
        except MissingError:
            _debug.logic("token_refused", reason="missing", document=document_id)
            return Doc

        if not (
            document_token.isascii()
            and consteq(document_token, document_sudo.document_token)
            and (
                document_sudo.user_permission != "none"
                or document_sudo.access_via_link != "none"
            )
        ):
            _debug.logic("token_refused", reason="mismatch", document=document_id)
            return Doc
        if not request.env.user._is_internal() and not document_sudo.active:
            _debug.logic("token_refused", reason="archived", document=document_id)
            return Doc

        skip_log = skip_log or request.env.user._is_public()
        if not skip_log:
            for doc_sudo in filter(
                bool, (document_sudo, document_sudo.shortcut_document_id)
            ):
                new_access = cls._upsert_last_access_date(request.env, doc_sudo)
                if new_access and doc_sudo._get_permission_without_token() == "none":
                    _debug.lifecycle("newly_accessible_via_link", document=doc_sudo)
                    document_sudo = document_sudo.with_context(
                        document_newly_accessible=True
                    )

        if follow_shortcut:
            if target_sudo := document_sudo.shortcut_document_id:
                if target_sudo.user_permission != "none" or (
                    target_sudo.access_via_link != "none"
                    and not target_sudo.is_access_via_link_hidden
                ):
                    _debug.pipeline(
                        "shortcut_followed", shortcut=document_sudo, target=target_sudo
                    )
                    document_sudo = target_sudo
                else:
                    _debug.logic("token_refused", reason="shortcut_target_hidden")
                    document_sudo = Doc

        if (
            request.env.user._is_public()
            and document_sudo.type == "binary"
            and not document_sudo.attachment_id
            and document_sudo.access_via_link != "edit"
        ):
            _debug.logic("token_refused", reason="public_empty_binary")
            return Doc

        _debug.logic(
            "token_resolved",
            document=document_sudo,
            permission=document_sudo.user_permission,
            via_link=document_sudo.access_via_link,
        )
        return document_sudo

    @classmethod
    def _upsert_last_access_date(cls, env: Any, document: Any) -> bool:
        env.cr.execute(
            SQL(
                """
                INSERT INTO document_access (document_id, partner_id, last_access_date)
                     VALUES (%(document_id)s, %(partner_id)s, %(now)s)
                ON CONFLICT (document_id, partner_id)
                  DO UPDATE SET last_access_date = EXCLUDED.last_access_date
                  RETURNING (xmax = 0) AS inserted
                """,
                document_id=document.id,
                partner_id=env.user.partner_id.id,
                now=fields.Datetime.now(),
            )
        )
        created = env.cr.fetchone()[0]
        _debug.perf.count("last_access_upserted", document=document, created=created)
        env["document.access"].invalidate_model(["last_access_date"])
        document.invalidate_recordset(["access_ids"])
        env["document.access.log"]._log(document, env.user.partner_id, "view")
        return created

    def _get_zip_response(self, name: str, documents: Any) -> Any:
        with _debug.perf("zip_plan", cr=request.env.cr, documents=documents) as span:
            entries = self._plan_zip_entries(name, documents)
            span.set(entries=len(entries))
        self._log_download(
            request.env["document.document"]
            .sudo()
            .browse({entry.document.id for entry in entries if entry.document})
        )
        headers = [
            ("Content-Type", "application/zip"),
            ("X-Content-Type-Options", "nosniff"),
            ("Content-Disposition", prepare_content_disposition_header(name)),
        ]
        return request.prepare_response(self._stream_zip(name, entries), headers)

    def _plan_zip_entries(self, name: str, documents: Any) -> list:
        seen_folders = set()
        seen_names = defaultdict(int)

        get_param = request.env["ir.config_parameter"].sudo().get_param
        max_files = int(
            get_param("document.zip_max_file_count", self.ZIP_MAX_FILE_COUNT)
        )
        max_total = int(
            get_param("document.zip_max_total_size", self.ZIP_MAX_TOTAL_SIZE)
        )
        counters = {"files": 0, "total": 0}

        def account(size: int, path: str) -> None:
            counters["files"] += 1
            counters["total"] += size + 2 * len(path.encode())
            if counters["files"] > max_files or counters["total"] > max_total:
                logger.warning(
                    "Refusing to build an oversized zip (%s files, %s bytes) for %r",
                    counters["files"],
                    counters["total"],
                    name,
                )
                _debug.logic(
                    "zip_refused",
                    reason="oversized",
                    files=counters["files"],
                    total=counters["total"],
                    max_files=max_files,
                    max_total=max_total,
                )
                raise RequestEntityTooLarge

        def unique(pathname: str) -> str:
            seen_names[pathname] += 1
            if seen_names[pathname] <= 1:
                return pathname

            ext = "".join(pathlib.Path(pathname).suffixes)
            return f"{pathname.removesuffix(ext)}-{seen_names[pathname]}{ext}"

        def get_zip_item(document: Any, folder: Any) -> Any:
            if document.type == "url":
                raise ValueError("cannot create a zip item out of an url")
            if not self._is_shortcut_target_reachable(document):
                _debug.logic("zip_item_skipped", reason="unreachable_target")
                return None
            if not document._is_download_allowed():
                _debug.logic("zip_item_skipped", reason="download_denied")
                return None
            if document.type == "folder":
                document_name = _normalize_zip_name(document.name)
                # it is the ending slash that makes it appears as a
                # folder inside the zip file.
                path = unique(f"{folder.path}{document_name}") + "/"
                # A directory holds no content, so its size is 0 -- but its
                # name is not free, and in a deep tree it is the whole cost.
                account(0, path)
                return ZipEntry(path, None, document)
            try:
                stream = self._documents_content_stream(
                    document.shortcut_document_id or document
                )
                download_name = _normalize_zip_name(stream.download_name)
            except ValueError, MissingError:
                _debug.logic("zip_item_skipped", reason="no_stream")
                return None
            if stream.type == "url":
                source = (document.shortcut_document_id or document).attachment_id
                reader = source.sudo()._get_zip_detached_reader()
                if reader is None:
                    return None
                path = unique(f"{folder.path}{download_name}")
                account(source.file_size or 0, path)
                return ZipEntry(path, stream, document, reader)
            path = unique(f"{folder.path}{download_name}")
            account(stream.size or 0, path)
            return ZipEntry(path, stream, document)

        def generate_zip_items(documents_sudo: Any, folder: Any) -> Any:
            documents_sudo = documents_sudo.sorted(lambda d: d.id)

            yield from (
                item
                for doc in documents_sudo
                if doc.type == "binary"
                and (doc.shortcut_document_id or doc).attachment_id
                if (item := get_zip_item(doc, folder)) is not None
            )
            for folder_sudo in documents_sudo:
                if folder_sudo.type != "folder":
                    continue
                source_sudo = folder_sudo.shortcut_document_id or folder_sudo

                if (sub_folder := get_zip_item(folder_sudo, folder)) is None:
                    continue
                yield sub_folder
                if source_sudo in seen_folders:
                    continue
                seen_folders.add(source_sudo)
                yield from generate_zip_items(
                    self._get_folder_children(source_sudo), sub_folder
                )

        return list(generate_zip_items(documents, ZipEntry("", None)))

    def _stream_zip(self, name: str, entries: list) -> Any:
        sink = _ZipSink()
        _debug.pipeline("zip_stream_start", name=name, entries=len(entries))
        try:
            with zipfile.ZipFile(
                sink, "w", compression=zipfile.ZIP_DEFLATED
            ) as doc_zip:
                for entry in entries:
                    if entry.stream is None:
                        doc_zip.writestr(entry.path, b"")
                        if chunk := sink.take():
                            yield chunk
                        continue
                    with doc_zip.open(entry.path, "w") as destination:
                        for block in _read_stream_blocks(entry.stream, entry.reader):
                            destination.write(block)
                            if chunk := sink.take():
                                yield chunk
                    if chunk := sink.take():
                        yield chunk
        except zipfile.BadZipfile:
            logger.exception("BadZipfile exception while building %r", name)
            raise
        if chunk := sink.take():
            yield chunk

    @staticmethod
    def _parse_pdf_split_new_files(new_files: Any) -> list:
        if not isinstance(new_files, list):
            e = "new_files must be a list"
            raise ValueError(e)
        for new_file in new_files:
            if not isinstance(new_file, dict):
                e = "each new file must be an object"
                raise ValueError(e)
            if not isinstance(new_file.get("name"), str):
                e = "each new file needs a name"
                raise ValueError(e)
            pages = new_file.get("new_pages")
            if not isinstance(pages, list):
                e = "new_pages must be a list"
                raise ValueError(e)
            for page in pages:
                if not isinstance(page, dict):
                    e = "each page must be an object"
                    raise ValueError(e)
                if page.get("old_file_type") not in ("document", "file"):
                    e = "old_file_type must be 'document' or 'file'"
                    raise ValueError(e)
                page["old_file_index"] = int(page.get("old_file_index"))
                page["old_page_number"] = int(page.get("old_page_number"))
        return new_files

    @http.route("/documents/pdf_split", type="http", methods=["POST"], auth="user")
    def pdf_split(
        self,
        new_files: str | None = None,
        ufile: Any = None,
        archive: Any = False,
        vals: str | None = None,
    ) -> Any:
        with replace_exceptions(ValueError, TypeError, by=BadRequest):
            vals = json.loads(vals or "{}")
            new_files = json.loads(new_files or "[]")
            new_files = self._parse_pdf_split_new_files(new_files)
            if not isinstance(vals, dict):
                e = "vals must be an object"
                raise ValueError(e)
        document_ids = {
            page["old_file_index"]
            for new_file in new_files
            for page in new_file["new_pages"]
            if page["old_file_type"] == "document"
        }
        documents = request.env["document.document"].browse(document_ids)
        documents.check_access("read")
        pdf_raws = [
            document.attachment_id.sudo()._get_pdf_raw()
            if document.attachment_id
            else None
            for document in documents
        ]
        if any(pdf_raw is None for pdf_raw in pdf_raws):
            _debug.logic("pdf_split_refused", reason="not_a_pdf", documents=documents)
            raise BadRequest("cannot split a document that does not hold a PDF")

        with ExitStack() as stack:
            files = request.httprequest.files.getlist("ufile")
            open_files = [
                stack.enter_context(io.BytesIO(file.read())) for file in files
            ]

            document_id_index_map = {}
            current_index = len(open_files)
            for document, pdf_raw in zip(documents, pdf_raws, strict=True):
                open_files.append(stack.enter_context(io.BytesIO(pdf_raw)))
                document_id_index_map[document.id] = current_index
                current_index += 1

            for new_file in new_files:
                for page in new_file["new_pages"]:
                    if page.pop("old_file_type") == "document":
                        page["old_file_index"] = document_id_index_map[
                            page["old_file_index"]
                        ]

            with _debug.perf(
                "pdf_split_request", cr=request.env.cr, sources=documents
            ) as span:
                with replace_exceptions(ValueError, by=BadRequest):
                    new_documents = documents._pdf_split(
                        new_files=new_files, open_files=open_files, vals=vals
                    )
                span.set(created=len(new_documents))

        if str2bool(archive, default=False):
            documents.write({"active": False})

        return request.prepare_response(
            json.dumps(new_documents.ids), [("Content-Type", "application/json")]
        )

    @http.route("/documents/<access_token>", type="http", auth="public")
    def documents_home(
        self,
        access_token: str,
        member_id: str = "",
        member_signup_token: str = "",
    ) -> Any:
        document_sudo = self._from_access_token(access_token)

        with replace_exceptions(ValueError, by=BadRequest):
            member_id = int(member_id or "0")

        if request.env.user._is_public():
            _debug.pipeline("home", audience="public", document=document_sudo)
            if not document_sudo:
                redirect_url = (
                    f"/documents/{quote(access_token, safe='')}?{keep_query('*')}"
                )
                if signup_url := request.env["document.access"]._get_signup_url(
                    member_id, member_signup_token, access_token, redirect_url
                ):
                    return request.redirect(signup_url)
            return self._documents_render_public_view(document_sudo)
        elif request.env.user._is_portal():
            _debug.pipeline("home", audience="portal", document=document_sudo)
            return self._documents_render_portal_view(document_sudo)
        else:
            _debug.pipeline("home", audience="internal", document=document_sudo)
            return request.redirect(
                f"/odoo/documents/{quote(access_token, safe='')}?{keep_query('*')}",
                HTTPStatus.TEMPORARY_REDIRECT,
            )

    def _documents_render_public_view(self, document_sudo: Any) -> Any:
        target_sudo = document_sudo.shortcut_document_id
        if (
            target_sudo
            and target_sudo.access_via_link != "none"
            and not target_sudo.is_access_via_link_hidden
        ):
            return request.redirect(
                f"/odoo/documents/{quote(target_sudo.access_token, safe='')}?{keep_query('*')}"
            )
        if target_sudo or not document_sudo:
            return request.render(
                "document.not_available", {"document": document_sudo}, status=404
            )
        if document_sudo.type == "url":
            if not _is_safe_redirect_url(document_sudo.url):
                return request.render(
                    "document.not_available", {"document": document_sudo}, status=404
                )
            return request.redirect(
                document_sudo.url, code=HTTPStatus.TEMPORARY_REDIRECT, local=False
            )
        if document_sudo.type == "binary" and document_sudo.attachment_id:
            return request.render(
                "document.share_file",
                {"document": document_sudo, "quote": lambda v: quote(v, safe="")},
            )
        if document_sudo.type == "binary":
            return request.render(
                "document.document_request_page",
                {"document": document_sudo, "quote": lambda v: quote(v, safe="")},
            )
        if document_sudo.type == "folder":
            sub_documents_sudo = ShareRoute._get_folder_children(document_sudo)
            return request.render(
                "document.public_folder_page",
                {
                    "folder": document_sudo,
                    "documents": sub_documents_sudo,
                    "subfolders": ShareRoute._get_folders_children(
                        sub_documents_sudo.filtered(lambda d: d.type == "folder")
                    ),
                    "quote": lambda v: quote(v, safe=""),
                },
            )
        else:
            e = f"unknown document type {document_sudo.type}"
            raise NotImplementedError(e)

    def _documents_render_portal_view(self, document: Any) -> Any:
        session_info = request.env["ir.http"].session_info()

        session_info.update(
            user_companies={
                "current_company": request.env.company.id,
                "allowed_companies": {
                    request.env.company.id: {
                        "id": request.env.company.id,
                        "name": request.env.company.name,
                    },
                },
            },
            documents_init=self._documents_get_init_data(document, request.env.user),
        )

        return request.render(
            "document.document_portal_view",
            {"session_info": session_info},
        )

    @classmethod
    def _documents_get_init_data(cls, document: Any, user: Any) -> dict:
        if not document or not user:
            return {}

        document.check_singleton()
        documents_init = {
            "user_folder_id": document.user_folder_id,
            "document_id": document.id,
        }
        if (
            document.active
            and document.type == "folder"
            and (
                not document.shortcut_document_id
                or document.shortcut_document_id.active
            )
        ):
            documents_init = {"user_folder_id": str(document.id)}
        elif document.active:
            target = document.shortcut_document_id or document
            if document.type == "binary" and target.attachment_id:
                documents_init["open_preview"] = True
        return documents_init

    @http.route(
        "/documents/avatar/<access_token>", type="http", auth="public", readonly=True
    )
    def documents_avatar(self, access_token: str) -> Any:
        partner_sudo = self._from_access_token(
            access_token, skip_log=True
        ).owner_id.partner_id
        return (
            request.env["ir.binary"]
            ._get_stream_image_from_record(
                partner_sudo,
                "avatar_128",
                placeholder=partner_sudo._get_avatar_placeholder_path(),
            )
            .prepare_response(as_attachment=False)
        )

    def _documents_content_readonly(self, rule: Any, args: dict) -> bool:
        if str2bool(request.httprequest.args.get("download", "1"), default=True):
            return False
        try:
            __, document_id = self._split_access_token(args.get("access_token") or "")
            if not document_id:
                return True
            document_sudo = (
                request.env["document.document"]
                .with_user(SUPERUSER_ID)
                .browse(document_id)
                .exists()
            )
            target_sudo = document_sudo.shortcut_document_id or document_sudo
            return target_sudo.type != "folder"
        except Exception:
            _debug.logic("readonly_classification_failed", token=bool(args))
            logger.warning(
                "Could not classify %r for read-only serving; using a read/write "
                "cursor",
                args.get("access_token"),
                exc_info=True,
            )
            return False

    @http.route(
        "/documents/content/<access_token>",
        type="http",
        auth="public",
        readonly=_documents_content_readonly,
    )
    def documents_content(self, access_token: str, download: Any = True) -> Any:
        document_sudo = self._from_access_token(access_token, skip_log=True)
        if not document_sudo:
            _debug.logic("content_refused", reason="no_document")
            raise request.prepare_not_found_error()
        if document_sudo.type == "url":
            if not _is_safe_redirect_url(document_sudo.url):
                _debug.logic("content_refused", reason="unsafe_redirect_scheme")
                raise request.prepare_not_found_error()
            _debug.pipeline("content_served", by="url_redirect", document=document_sudo)
            return request.redirect(
                document_sudo.url, code=HTTPStatus.TEMPORARY_REDIRECT, local=False
            )
        if document_sudo.type == "folder":
            if not document_sudo._is_download_allowed():
                _debug.logic("content_refused", reason="folder_download_denied")
                raise Forbidden("downloading this folder is not allowed")
            _debug.pipeline("content_served", by="folder_zip", document=document_sudo)
            self._log_download(document_sudo)
            return self._get_zip_response(
                f"{document_sudo.name}.zip",
                self._get_folder_children(document_sudo),
            )
        if document_sudo.type == "binary":
            if not document_sudo.attachment_id:
                _debug.logic("content_refused", reason="no_attachment")
                raise request.prepare_not_found_error()
            with replace_exceptions(ValueError, by=BadRequest):
                download = str2bool(download)
            if download:
                if not document_sudo._is_download_allowed():
                    _debug.logic("content_refused", reason="download_denied")
                    raise Forbidden("downloading this document is not allowed")
                self._log_download(document_sudo)
            elif not document_sudo._is_inline_content_allowed():
                _debug.logic("content_refused", reason="inline_download_denied")
                raise Forbidden("downloading this document is not allowed")
            else:
                self._log_view(document_sudo)
            _debug.pipeline(
                "content_served",
                by="binary",
                document=document_sudo,
                download=download,
            )
            with replace_exceptions(
                ValueError, MissingError, by=request.prepare_not_found_error()
            ):
                stream = self._documents_content_stream(document_sudo)
            return stream.prepare_response(as_attachment=download)
        e = f"unknown document type {document_sudo.type!r}"
        raise NotImplementedError(e)

    def _documents_content_stream(self, document_sudo: Any) -> Any:
        return request.env["ir.binary"]._get_stream_from_record(document_sudo)

    def _log_download(self, document_sudo: Any) -> None:
        _debug.lifecycle("download_logged", documents=document_sudo)
        request.env["document.access.log"].sudo()._log(
            document_sudo, request.env.user.partner_id, "download"
        )

    def _log_view(self, document_sudo: Any) -> None:
        _debug.lifecycle("view_logged", documents=document_sudo)
        request.env["document.access.log"].sudo()._log(
            document_sudo, request.env.user.partner_id, "view"
        )

    @http.route(
        "/documents/redirect/<access_token>", type="http", auth="public", readonly=True
    )
    def document_redirect(self, access_token: str) -> Any:
        return request.redirect(
            f"/odoo/documents/{quote(access_token, safe='')}",
            HTTPStatus.MOVED_PERMANENTLY,
        )

    @http.route("/documents/touch/<access_token>", type="jsonrpc", auth="user")
    def documents_touch(self, access_token: str) -> dict:
        doc = self._from_access_token(access_token)
        if doc.env.context.get("document_newly_accessible"):
            return {"reload": True}
        return {}

    @http.route(
        [
            "/documents/thumbnail/<access_token>",
            "/documents/thumbnail/<access_token>/<int:width>x<int:height>",
        ],
        type="http",
        auth="public",
        readonly=True,
    )
    def documents_thumbnail(
        self, access_token: str, width: str = "0", height: str = "0", unique: str = ""
    ) -> Any:
        with replace_exceptions(ValueError, by=BadRequest):
            width = int(width)
            height = int(height)
            if width < 0 or height < 0:
                e = "width and height must be positive"
                raise ValueError(e)
        send_file_kwargs = {}
        if unique:
            send_file_kwargs["immutable"] = True
            send_file_kwargs["max_age"] = http.STATIC_CACHE_LONG
        document_sudo = self._from_access_token(access_token, skip_log=True)
        return (
            request.env["ir.binary"]
            ._get_stream_image_from_record(
                document_sudo, "thumbnail", width=width, height=height
            )
            .prepare_response(as_attachment=False, **send_file_kwargs)
        )

    @http.route(
        ["/documents/thumbnail_textual/<access_token>"],
        type="http",
        auth="public",
        readonly=True,
    )
    def documents_thumbnail_textual(self, access_token: str) -> Any:
        document_sudo = self._from_access_token(access_token, skip_log=True)
        if not document_sudo:
            raise request.prepare_not_found_error()
        if document_sudo.type != "binary":
            _debug.logic(
                "thumbnail_textual_refused", reason="not_binary", document=document_sudo
            )
            e = f"bad document type: expected a file (binary) document, found a {document_sudo.type} document"
            raise BadRequest(e)
        attachment_sudo = document_sudo.attachment_id.sudo()
        if not attachment_sudo:
            raise request.prepare_not_found_error()
        if not is_mimetype_textual(document_sudo.mimetype):
            _debug.logic(
                "thumbnail_textual_refused",
                reason="not_textual",
                mimetype=document_sudo.mimetype,
            )
            e = f"bad document mimetype: expect text/* or a recognized application/, got {document_sudo.mimetype}"
            raise BadRequest(e)
        if document_sudo.mimetype == "text/html" or not (
            head := attachment_sudo._get_content_prefix(self.TEXTUAL_THUMBNAIL_SIZE)
        ):
            # These two branches serve the WHOLE file, not a 4 KB head, so they
            # answer the same question `/documents/content` does and take the
            # same gate rather than a different one.
            if not document_sudo._is_inline_content_allowed():
                _debug.logic(
                    "thumbnail_textual_refused",
                    reason="inline_download_denied",
                    document=document_sudo,
                )
                raise Forbidden("downloading this document is not allowed")
            with replace_exceptions(
                ValueError, MissingError, by=request.prepare_not_found_error()
            ):
                stream = self._documents_content_stream(document_sudo)
            return stream.prepare_response(as_attachment=False)
        return request.render(
            "document.thumbnails_textual",
            {
                "content": head.decode("utf-8", errors="replace"),
            },
        )

    @http.route(
        ["/documents/document/<int:document_id>/update_thumbnail"],
        type="jsonrpc",
        auth="user",
    )
    def documents_update_thumbnail(self, document_id: int, thumbnail: Any) -> None:
        document = request.env["document.document"].browse(document_id)
        # A read check guarding a `sudo().write`: any reader could set the
        # stored thumbnail that every other user then sees, and because the
        # write flips `thumbnail_status` away from "client_generated" nobody
        # could correct it afterwards. The thumbnail is a property of the
        # document, so writing it takes write access like every other one; the
        # client only reaches this route for documents it can already edit, and
        # a viewer simply leaves the thumbnail to somebody who can.
        document.check_access("write")
        if document.thumbnail_status != "client_generated":
            return
        validated = False
        if thumbnail:
            with replace_exceptions(Exception, by=BadRequest("invalid thumbnail")):
                image = base64_to_image(thumbnail)
                image.thumbnail((200, 140))
                buffer = io.BytesIO()
                image.convert("RGB").save(buffer, format="PNG")
                validated = base64.b64encode(buffer.getvalue())
        document.sudo().write(
            {
                "thumbnail": validated,
                "thumbnail_status": "present" if validated else "error",
            }
        )

    @http.route(["/documents/zip"], type="http", auth="user")
    def documents_zip(self, file_ids: str, zip_name: str, **kw: Any) -> Any:
        with replace_exceptions(ValueError, by=BadRequest):
            ids_list = [int(x) for x in file_ids.split(",")]
        documents = request.env["document.document"].browse(ids_list)
        documents.check_access("read")
        return self._get_zip_response(zip_name, documents)

    @http.route(
        ["/documents/upload/", "/documents/upload/<access_token>"],
        type="http",
        auth="public",
        methods=["POST"],
        max_content_length=_max_content_length,
    )
    def documents_upload(
        self,
        ufile: Any,
        access_token: str = "",
        user_folder_id: str = "",
        owner_id: str = "",
        partner_id: str = "",
        res_id: str = "",
        res_model: Any = False,
        allowed_company_ids: str = "",
        cloud_storage: str = "",
        file_size: str = "",
        **kw: Any,
    ) -> Any:
        if allowed_company_ids:
            with replace_exceptions(ValueError, by=BadRequest):
                request.update_context(
                    allowed_company_ids=json.loads(allowed_company_ids)
                )
        with replace_exceptions(ValueError, by=BadRequest):
            upload_root = UserFolder.parse(user_folder_id)
        if (access_token and upload_root) or (
            not access_token
            and (upload_root is None or not upload_root.is_writable_root)
        ):
            _debug.logic("upload_refused", reason="token_and_root_conflict")
            raise BadRequest("Incorrect token/user_folder_id values")
        is_internal_user = request.env.user._is_internal()
        if is_internal_user and not access_token:
            document_sudo = request.env["document.document"].sudo()
        else:
            document_sudo = self._from_access_token(access_token)
            if (
                not document_sudo
                or (
                    document_sudo.user_permission != "edit"
                    and document_sudo.access_via_link != "edit"
                )
                or document_sudo.type not in ("binary", "folder")
            ):
                _debug.logic("upload_refused", reason="target_not_writable")
                raise request.prepare_not_found_error()

        files = request.httprequest.files.getlist("ufile")
        if not files:
            _debug.logic("upload_refused", reason="no_files")
            raise BadRequest("missing files")
        if len(files) > 1 and document_sudo.type not in (False, "folder"):
            _debug.logic("upload_refused", reason="many_files_one_document")
            raise BadRequest("cannot save multiple files inside a single document")
        if cloud_storage:
            self._check_direct_upload(files)

        if is_internal_user:
            with replace_exceptions(ValueError, by=BadRequest):
                owner_id = (
                    int(owner_id)
                    if owner_id
                    else request.env.user.id
                    if not user_folder_id
                    else None
                )
                partner_id = int(partner_id) if partner_id else None
                res_id = int(res_id) if res_id else False
            values_are_used = document_sudo.type in (False, "folder")
            if (
                values_are_used
                and owner_id
                and owner_id != request.env.user.id
                and not request.env.user.has_group("document.group_documents_manager")
            ):
                _debug.logic("upload_refused", reason="owner_not_self")
                raise Forbidden("cannot upload on behalf of another user")
            if values_are_used and res_model and res_id:
                if res_model not in request.env:
                    _debug.logic("upload_refused", reason="unknown_res_model")
                    raise BadRequest("unknown res_model")
                request.env[res_model].browse(res_id).check_access("write")
        elif owner_id or partner_id or res_id or res_model:
            _debug.logic("upload_refused", reason="values_need_internal_user")
            raise Forbidden("only internal users can provide field values")
        else:
            owner_id = (
                document_sudo.owner_id.id
                if request.env.user._is_public()
                else request.env.user.id
            )
            partner_id = None
            res_model = False
            res_id = False

        previous_attachment_id = document_sudo.attachment_id
        with _debug.perf(
            "upload", cr=request.env.cr, files=len(files), target=document_sudo
        ) as span:
            document_ids = self._documents_upload(
                document_sudo,
                files,
                owner_id,
                user_folder_id,
                partner_id,
                res_id,
                res_model,
            )
            span.set(created=len(document_ids))
        if document_sudo.type != "folder" and len(document_ids) == 1:
            document_sudo = document_sudo.browse(document_ids)

        if cloud_storage:
            return self._documents_direct_upload_response(document_ids, file_size)
        if request.env.user._is_public():
            if document_sudo.type == "folder" or previous_attachment_id:
                return request.redirect(document_sudo.access_url)
            return request.redirect("/documents/upload/success")
        else:
            return request.prepare_json_response(document_ids)

    def _check_direct_upload(self, files: list) -> None:
        if len(files) > 1:
            _debug.logic("direct_upload_refused", reason="many_files")
            raise BadRequest("a direct cloud upload carries one file")
        if (
            not request.env["ir.config_parameter"]
            .sudo()
            .get_param("cloud_storage_provider")
        ):
            _debug.logic("direct_upload_refused", reason="no_provider")
            raise BadRequest(
                "Cloud storage configuration has been changed. Please refresh the page."
            )

    def _documents_direct_upload_response(
        self, document_ids: list, file_size: str
    ) -> Any:
        document_sudo = request.env["document.document"].sudo().browse(document_ids)
        document_sudo.check_singleton()
        attachment_sudo = document_sudo.attachment_id
        attachment_sudo._post_add_create(cloud_storage=True)
        if attachment_sudo.type != "cloud_storage":
            _debug.logic("direct_upload_refused", reason="not_cloud_storage")
            raise BadRequest(
                "Cloud storage configuration has been changed. Please refresh the page."
            )
        if file_size:
            with replace_exceptions(ValueError, by=BadRequest):
                attachment_sudo.file_size = int(file_size)
        return request.prepare_json_response(
            {
                "document_ids": document_ids,
                "upload_info": attachment_sudo._generate_cloud_storage_upload_info(),
            }
        )

    def _documents_upload(
        self,
        document_sudo: Any,
        files: Any,
        owner_id: Any,
        user_folder_id: str,
        partner_id: Any,
        res_id: Any,
        res_model: Any,
    ) -> list:
        is_internal_user = request.env.user._is_internal()

        created_sudo = request.env["document.document"].sudo()
        AttachmentSudo = (
            request.env["ir.attachment"]
            .sudo(not is_internal_user)
            .with_context(image_no_postprocess=True)
        )

        if document_sudo.type == "binary":
            _debug.pipeline("upload_plan", by="replace_binary", document=document_sudo)
            attachment_sudo = AttachmentSudo._create_from_request_file(
                files[0], mimetype="TRUST" if is_internal_user else "GUESS"
            )
            res_model, res_id = document_sudo._owning_record_link()
            attachment_sudo.with_context(no_document=True).write(
                {"res_model": res_model, "res_id": res_id}
            )
            values = {"attachment_id": attachment_sudo.id}
            if not document_sudo.attachment_id:
                if document_sudo.access_via_link == "edit":
                    _debug.logic("upload_request_fulfilled", document=document_sudo)
                    values["access_via_link"] = "view"
            self._documents_upload_create_write(document_sudo, values)
            created_sudo = document_sudo
        else:
            folder_sudo = document_sudo
            _debug.pipeline(
                "upload_plan", by="into_folder", folder=folder_sudo, files=len(files)
            )
            location = (
                {"user_folder_id": user_folder_id}
                if user_folder_id
                else {"folder_id": folder_sudo.id}
            )
            uploader_access = (
                [
                    Command.create(
                        {
                            "partner_id": request.env.user.partner_id.id,
                            "role": "edit",
                        }
                    )
                ]
                if UserFolder.parse(user_folder_id) == UserFolder(UserFolder.COMPANY)
                else []
            )
            # The attachments are created one per file because
            # `_create_from_request_file` is per-file by construction -- it may
            # stream a large upload straight to the filestore. The DOCUMENTS are
            # not: they are prepared per file and created in ONE call, so a
            # thirty-file drop pays one document INSERT, one `parent_path`
            # maintenance pass and one recompute flush instead of thirty of
            # each.
            pending_vals = []
            for file in files:
                vals = (
                    {
                        "attachment_id": AttachmentSudo._create_from_request_file(
                            file, mimetype="TRUST" if is_internal_user else "GUESS"
                        ).id,
                        "type": "binary",
                        "access_via_link": "none"
                        if folder_sudo.access_via_link in (False, "none")
                        else "view",
                        **location,
                        "owner_id": owner_id,
                        "res_model": res_model or False,
                        "res_id": res_id,
                    }
                    | ({"partner_id": partner_id} if partner_id is not None else {})
                    | ({"access_ids": uploader_access} if uploader_access else {})
                )
                prepared = self._documents_upload_prepare(folder_sudo, vals)
                if prepared is None:
                    continue
                if isinstance(prepared, dict):
                    prepared.setdefault("folder_id", folder_sudo.id)
                    pending_vals.append(prepared)
                else:
                    created_sudo |= prepared
            if pending_vals:
                new_documents_sudo = folder_sudo.create(pending_vals)
                for new_document_sudo, new_vals in zip(
                    new_documents_sudo, pending_vals, strict=True
                ):
                    self._documents_upload_post(new_document_sudo, new_vals)
                created_sudo |= new_documents_sudo

        return created_sudo.ids

    def _documents_upload_prepare(self, document_sudo: Any, vals: dict) -> Any:
        """Decide what one uploaded file becomes, before anything is created.

        Return the values to create (or write), `None` to drop the file, or an
        existing `document.document` to report instead of creating one. This
        runs per file; creation is batched behind it, so an override that needs
        to inspect or refuse an upload belongs here rather than around the
        create itself.
        """
        return vals

    def _documents_upload_post(self, document_sudo: Any, vals: dict) -> None:
        """React to one document that an upload just created or replaced."""
        _debug.lifecycle("uploaded", document=document_sudo, fields=sorted(vals))
        if any(field_name in vals for field_name in ["raw", "datas", "attachment_id"]):
            document_sudo.message_post(
                body=_("Document uploaded by %(user)s", user=request.env.user.name)
            )

    def _documents_upload_create_write(self, document_sudo: Any, vals: dict) -> Any:
        """Single-document upload: replacing a binary, or one file into a folder.

        The multi-file folder path does not come through here -- it batches the
        create and calls `_documents_upload_prepare` / `_documents_upload_post`
        directly, which is why those two, not this one, are the extension
        points.
        """
        prepared = self._documents_upload_prepare(document_sudo, vals)
        if prepared is None:
            return request.env["document.document"].sudo()
        if not isinstance(prepared, dict):
            return prepared
        if document_sudo.type == "binary":
            document_sudo.write(prepared)
        else:
            prepared.setdefault("folder_id", document_sudo.id)
            document_sudo = document_sudo.create(prepared)
        self._documents_upload_post(document_sudo, prepared)
        return document_sudo

    @http.route("/documents/upload/success", type="http", auth="public")
    def documents_upload_success(self) -> Any:
        return request.render("document.document_request_done_page")

    @http.route(
        "/documents/upload_traceback",
        type="http",
        methods=["POST"],
        auth="user",
        max_content_length=1 << 20,
    )
    def documents_upload_traceback(self, ufile: Any, **kw: Any) -> Any:
        if not request.env.user._is_internal():
            raise Forbidden

        folder_sudo = request.env["document.document"]._get_traceback_folder_sudo()

        files = request.httprequest.files.getlist("ufile")
        if not files:
            raise BadRequest("missing files")
        if len(files) > 1:
            raise BadRequest("This route only accepts one file at a time.")

        traceback_sudo = self._documents_upload_create_write(
            folder_sudo,
            {
                "attachment_id": request.env["ir.attachment"]
                ._create_from_request_file(files[0], mimetype="text/plain")
                .id,
                "type": "binary",
                "access_internal": "none",
                "access_via_link": "view",
                "folder_id": folder_sudo.id,
                "owner_id": False,
            },
        )

        return request.prepare_json_response([traceback_sudo.access_url])


class DocumentsAttachmentController(AttachmentController):
    @http.route()
    def mail_attachment_upload(self, *args: Any, **kw: Any) -> Any:
        if kw.get("activity_id"):
            with replace_exceptions(ValueError, by=BadRequest):
                activity_id = int(kw["activity_id"])
            document = request.env["document.document"].search(
                [("request_activity_id", "=", activity_id)], limit=1
            )
            if document:
                request.update_context(no_document=True)
        return super().mail_attachment_upload(*args, **kw)

    @http.route(
        "/documents/content/pdf_first_page/<access_token>",
        methods=["GET"],
        type="http",
        auth="public",
        readonly=True,
    )
    def document_attachment_pdf_first_page(
        self, access_token: str | None = None
    ) -> Any:
        document_sudo = ShareRoute._from_access_token(access_token, skip_log=True)
        if not document_sudo.attachment_id:
            raise request.prepare_not_found_error()
        if (document_sudo.mimetype or "") != "application/pdf":
            raise BadRequest("document is not a PDF")
        return self._get_pdf_first_page_response(document_sudo.attachment_id)
