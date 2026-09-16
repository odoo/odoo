import base64
import collections
import contextlib
import csv
import datetime
import difflib
import functools
import hashlib
import importlib.util
import io
import itertools
import logging
import operator
import re
import threading
import unicodedata
from collections.abc import Sequence
from pathlib import Path

import psycopg
from PIL import Image

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.libs.documents import (
    ROWS,
    BaseReader,
    decode,
    guess_encoding,
    infer_separators,
    mimetype_for,
    mimetypes_for,
    register_reader,
    strip_currency_symbol,
)
from odoo.libs.filesystem import guess_mimetype
from odoo.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    config,
)
from odoo.tools.translate import _

FIELDS_RECURSION_LIMIT = 3
ERROR_PREVIEW_BYTES = 200
DEFAULT_CHUNK_SIZE = 32768
# Number of rows the separator sniffer looks at. Sniffing used to build a full
# csv.reader pass over the *whole* decoded file for each candidate delimiter;
# the shape of a file is decided by its first lines, so cap the work.
SEPARATOR_SNIFF_ROWS = 100
_logger = logging.getLogger(__name__)
MIMETYPE_TO_READER = {
    mimetype_for(extension): extension for extension in ("csv", "xls", "xlsx", "ods")
}

# Explicit allow-list of the formats `_read_file` may dispatch to. This exists
# so a file *name* can never select the method that reads it: `_read_file` used
# to do `getattr(self, '_read_' + <suffix of the uploaded filename>)`, which
#   * resolved `foo.file` to `_read_file` itself -> unbounded self-recursion.
#     Each frame then logged its own chained traceback, and because every level
#     re-renders the whole `__context__` chain the log output is quadratic:
#     one upload produced ~490 recursions, ~980 WARNING records and ~240 MiB of
#     log text, pinning a worker for ~60s (measured over HTTP);
#   * exposed unrelated ORM internals (`foo.group` -> `_read_group`,
#     `foo.format` -> `_read_format`, ...) to filename-driven invocation.
# Keys are lower-cased extensions without the dot; `xlsm` is macro-enabled xlsx
# and is read by the same handler (the UI already accepts it).
EXTENSION_TO_READER = {
    "csv": "_read_csv",
    "ods": "_read_ods",
    "xls": "_read_xls",
    "xlsm": "_read_xlsx",
    "xlsx": "_read_xlsx",
}

# The options the readers consume. Everything else -- `has_headers`, `skip`,
# `limit`, the date and number formats -- is applied to the rows *after* the
# file has been read, so it cannot change what a parse produces.
PARSE_OPTION_KEYS = ("encoding", "separator", "quoting", "sheet")
# ...and the ones the readers write back into `options`: the sheet list a
# workbook turned out to have, and the encoding/separator/quoting they guessed.
# A cache hit has to replay these or the client stops being told about them.
PARSE_OPTION_OUTPUTS = (*PARSE_OPTION_KEYS, "sheets")
# Entries kept, and the size above which a result is parsed but not kept. The
# pair bounds what one worker can hold to roughly what an import's own row lists
# already cost, rather than to whatever a 64 MiB upload expands to. A file over
# the cell budget simply behaves as it did before.
PARSED_FILE_CACHE_ENTRIES = 4
PARSED_FILE_CACHE_MAX_CELLS = 500_000


def _copy_option_outputs(outputs):
    """A caller-owned copy of the options a reader wrote.

    Only ``sheets`` is mutable today; copying by type rather than by name keeps
    that from being a fact this function has to be told again.
    """
    return {
        name: list(value) if isinstance(value, list) else value
        for name, value in outputs.items()
    }


class _ParsedFileCache:
    """Rows keyed by file content, so a batched import parses its file once.

    ``execute_import`` re-reads the upload from scratch on every batch -- the
    batches are separate RPC calls, and nothing carried the parse between them.
    That is O(batches x file) and the readers are not cheap: measured on a
    5,000-row xlsx imported at limit 500, **18% of the entire import** (1.97 s
    of 10.7 s) went on parsing the same workbook eleven times, and a
    20,000-row .ods costs 1.4 s per read, so ten batches burn 12.5 s producing
    eleven identical lists.

    Keyed on a digest of the file rather than on the import record, for a
    reason that is easy to get wrong: ``write_date`` is the *transaction*
    timestamp, so two writes to ``file`` inside one transaction share it and a
    record-keyed entry would serve the old rows for the new file. Content is
    also the honest key -- the same bytes parse to the same rows whichever
    record they arrived on.

    Safe to hand the same rows to several callers because nothing downstream
    mutates them: ``_convert_import_data`` copies each row it keeps
    (``list(mapper(row))``) and every in-place stage from ``_parse_import_data``
    on works on those copies. The outer list is copied per caller anyway, so a
    caller that pops from it -- ``parse_preview`` does -- cannot reach the
    entry.
    """

    def __init__(self, entries, max_cells):
        self._entries = entries
        self._max_cells = max_cells
        self._store = collections.OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            hit = self._store.get(key)
            if hit is not None:
                self._store.move_to_end(key)
            return hit

    def set(self, key, rows, outputs):
        if sum(len(row) for row in rows) > self._max_cells:
            return
        with self._lock:
            self._store[key] = (rows, outputs)
            self._store.move_to_end(key)
            while len(self._store) > self._entries:
                self._store.popitem(last=False)

    def clear(self):
        with self._lock:
            self._store.clear()


PARSED_FILE_CACHE = _ParsedFileCache(
    PARSED_FILE_CACHE_ENTRIES, PARSED_FILE_CACHE_MAX_CELLS
)

CONCAT_SEPARATOR_IMPORT = {
    "char": " ",
    "text": "\n",
    "html": "<br>",
    "many2many": ",",
}


class _StoredCurrencySymbols:
    """The symbols this database knows, asked one at a time.

    A ``Container`` rather than a set because the caller that reaches here has
    no symbol table to hand and wants exactly one query, for the one symbol the
    value turned out to carry.
    """

    def __init__(self, env):
        self.env = env

    def __contains__(self, symbol):
        return bool(
            self.env["res.currency"].search_count([("symbol", "=", symbol)], limit=1)
        )


class ImportValidationError(Exception):
    """
    This class is made to correctly format all the different error types that
    can occur during the pre-validation of the import that is made before
    calling the data loading itself. The Error data structure is meant to copy
    the one of the errors raised during the data loading. It simplifies the
    error management at client side as all errors can be treated the same way.

    This exception is typically raised when there is an error during data
    parsing (image, int, dates, etc..) or if the user did not select at least
    one field to map with a column.
    """

    def __init__(self, message, **kwargs):
        super().__init__(message)
        self.type = kwargs.get("error_type", "error")
        self.message = message
        self.record = False
        self.not_matching_error = True
        self.field_path = [kwargs["field"]] if kwargs.get("field") else False
        self.field_type = kwargs.get("field_type")


def read_xls_rows(data, options):
    # Lazy import, mirroring _read_xlsx's `import openpyxl` and _read_ods's
    # `from . import odf_ods_reader`: `xlrd` is an optional format library
    # (not in requirements.txt, unlike chardet/Pillow/psycopg above), and a
    # module-level `import xlrd` used to make the WHOLE base_import module
    # fail to load if it were ever absent, instead of only ".xls" support
    # becoming unavailable via _read_file's existing `except ImportError`
    # handling (t24068 F20).
    import xlrd

    book = xlrd.open_workbook(file_contents=data)
    sheets = options["sheets"] = book.sheet_names()
    sheet_name = options["sheet"] = options.get("sheet") or sheets[0]
    sheet = book.sheet_by_name(sheet_name)
    rows = []
    for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
        values = []
        for colx, cell in enumerate(row, 1):
            if cell.ctype is xlrd.XL_CELL_NUMBER:
                if cell.value % 1 == 0:
                    values.append(str(int(cell.value)))
                else:
                    values.append(str(cell.value))
            elif cell.ctype is xlrd.XL_CELL_DATE:
                dt = datetime.datetime(
                    *xlrd.xldate.xldate_as_tuple(cell.value, book.datemode)
                )
                values.append(dt if cell.value % 1 else dt.date())
            elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                values.append("True" if cell.value else "False")
            elif cell.ctype is xlrd.XL_CELL_ERROR:
                raise ImportValidationError(
                    _(
                        "Invalid cell value at row %(row)s, column %(col)s: %(cell_value)s",
                        row=rowx,
                        col=colx,
                        cell_value=xlrd.error_text_from_code.get(
                            cell.value, _("unknown error code %s", cell.value)
                        ),
                    )
                )
            else:
                values.append(cell.value)
        if any(x and (not isinstance(x, str) or x.strip()) for x in values):
            rows.append(values)
    return rows


def read_xlsx_rows(data, options):
    import openpyxl
    import openpyxl.cell.cell as types
    import openpyxl.styles.numbers as styles

    from .zip_guard import check_zip_member_sizes

    check_zip_member_sizes(io.BytesIO(data))
    book = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    try:
        sheets = options["sheets"] = book.sheetnames
        sheet_name = options["sheet"] = options.get("sheet") or sheets[0]
        sheet = book[sheet_name]
        rows = []
        for rowx, row in enumerate(sheet.rows, 1):
            values = []
            for colx, cell in enumerate(row, 1):
                if cell.data_type == types.TYPE_ERROR:
                    raise ImportValidationError(
                        _(
                            "Invalid cell value at row %(row)s, column %(col)s: %(cell_value)s",
                            row=rowx,
                            col=colx,
                            cell_value=cell.value,
                        )
                    )

                if cell.value is None:
                    values.append("")
                elif isinstance(cell.value, float):
                    if cell.value % 1 == 0:
                        values.append(str(int(cell.value)))
                    else:
                        values.append(str(cell.value))
                elif cell.is_date:
                    d_fmt = styles.is_datetime(cell.number_format)
                    if d_fmt == "datetime":
                        values.append(cell.value)
                    elif d_fmt == "date":
                        values.append(cell.value.date())
                    else:
                        raise ImportValidationError(
                            _(
                                "Invalid cell format at row %(row)s, column %(col)s: %(cell_value)s, with format: %(cell_format)s, as (%(format_type)s) formats are not supported.",
                                row=rowx,
                                col=colx,
                                cell_value=cell.value,
                                cell_format=cell.number_format,
                                format_type=d_fmt,
                            )
                        )
                else:
                    values.append(str(cell.value))

            if any(x and (not isinstance(x, str) or x.strip()) for x in values):
                rows.append(values)
        return rows
    finally:
        book.close()


class _SpreadsheetReader(BaseReader):
    """A workbook read as `rows`, for every consumer of the format layer.

    These live here rather than in `libs/documents` because xlrd,
    openpyxl and odfpy are optional and this module is where they are declared.

    The document's own options are handed to the reader, not an empty dict. The
    readers write the workbook's sheet names back into what they are given, so
    passing `{}` discarded them: a consumer of `Document.rows` got the first
    sheet with no way to learn there had been others, or to ask for one. The
    default is unchanged -- no `sheet` still means the first -- and a caller
    that does know which it wants can now say so.

    One document is one sheet, because `_derive` caches. Reading a second sheet
    means a second `Document`, which is what `base_import.import` already does:
    `sheet` is part of its parsed-file cache key.
    """

    yields = (ROWS,)

    def __init__(self, name, mimetypes, reader, module):
        self.name = name
        self.mimetypes = frozenset(mimetypes)
        self._reader = reader
        self._module = module

    def read(self, document):
        return self._reader(document.data, document.options)

    def provides(self, document):
        return importlib.util.find_spec(self._module) is not None


def read_ods_rows(data, options):
    from . import odf_ods_reader

    doc = odf_ods_reader.ODSReader(file=io.BytesIO(data))
    sheets = options["sheets"] = list(doc.sheets)
    if not sheets:
        raise ImportValidationError(_("Import file has no content or is corrupt"))
    # A stale/hand-crafted `sheet` option must not IndexError or KeyError
    # its way out of the reader; fall back to the first sheet.
    sheet = options.get("sheet")
    if sheet not in doc.sheets:
        sheet = sheets[0]
    options["sheet"] = sheet

    # The reader already drops blank rows, including the repeated blank
    # tail every producer writes.
    return doc.get_sheet(sheet)


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def get_import_templates(self):
        """
        Get the import templates label and path.

        :return: a list(dict) containing label and template path
                 like ``[{'label': 'foo', 'template': 'path'}]``
        """
        return []


class Base_ImportMapping(models.Model):
    """Remembers column-to-field mappings from a previous import for reuse."""

    _name = "base_import.mapping"
    _description = "Base Import Mapping"

    res_model = fields.Char(
        index=True,
        required=True,
    )
    column_name = fields.Char(required=True)
    field_name = fields.Char(required=True)

    _column_unique_per_model = models.Constraint(
        "UNIQUE(res_model, column_name)",
        "A column name can only be mapped to one field per model.",
    )


class ResUsers(models.Model):
    _inherit = "res.users"

    def _can_import_remote_urls(self):
        """Hook to decide whether the current user is allowed to import
        images via URL (as such an import can DOS a worker). By default,
        allows the administrator group.

        :rtype: bool
        """
        self.check_singleton()
        return self._is_admin()


class Base_ImportImport(models.TransientModel):
    """Prepares and executes the import of a user-uploaded file into an Odoo model."""

    _name = "base_import.import"
    _description = "Base Import"

    # allow imports to survive for 12h in case user is slow
    _transient_max_hours = 12.0
    # we consider that if the difference is more than 0.2, then the two compared strings are "too different" to propose
    # any match between them. (see '_get_mapping_suggestion' for more details)
    FUZZY_MATCH_DISTANCE = 0.2

    res_model = fields.Char(string="Model")
    file = fields.Binary(
        attachment=False,
        help="File to check and/or import, raw binary (not base64)",
    )
    file_name = fields.Char()
    file_type = fields.Char()

    @api.model
    def get_fields_tree(self, model, depth=FIELDS_RECURSION_LIMIT):
        """Recursively get fields for the provided model (through
        fields_get) and filter them according to importability

        The output format is a list of :class:`Field`:

        .. class:: Field

            .. attribute:: id: str

                A non-unique identifier for the field, used to compute
                the span of the ``required`` attribute: if multiple
                ``required`` fields have the same id, only one of them
                is necessary.

            .. attribute:: name: str

                The field's logical (Odoo) name within the scope of
                its parent.

            .. attribute:: string: str

                The field's human-readable name (``@string``)

            .. attribute:: required: bool

                Whether the field is marked as required in the
                model. Clients must provide non-empty import values
                for all required fields or the import will error out.

            .. attribute:: fields: list[Field]

                The current field's subfields. The database and
                external identifiers for m2o and m2m fields; a
                filtered and transformed fields_get for o2m fields (to
                a variable depth defined by ``depth``).

                Fields with no sub-fields will have an empty list of
                sub-fields.

            .. attribute:: model_name: str

                Used in the Odoo Field Tooltip on the import view
                and to get the model of the field of the related field(s).
                Name of the current field's model.

            .. attribute:: comodel_name: str

                Used in the Odoo Field Tooltip on the import view
                and to get the model of the field of the related field(s).
                Name of the current field's comodel, i.e. if the field is a relation field.

        Structure example for 'crm.team' model for returned importable_fields::

            [
                {'name': 'message_ids', 'string': 'Messages', 'model_name': 'crm.team', 'comodel_name': 'mail.message', 'fields': [
                    {'name': 'moderation_status', 'string': 'Moderation Status', 'model_name': 'mail.message', 'fields': []},
                    {'name': 'body', 'string': 'Contents', 'model_name': 'mail.message', 'fields' : []}
                ]},
                {{'name': 'name', 'string': 'Sales Team', 'model_name': 'crm.team', 'fields' : []}
            ]

        :param str model: name of the model to get fields form
        :param int depth: depth of recursion into o2m fields, clamped to
            :data:`FIELDS_RECURSION_LIMIT`
        """
        # This method is a public (RPC-callable) entry point and `depth` is
        # caller-supplied, so it is an unauthenticated-shaped amplification
        # knob: each extra level multiplies the result by ~2-4x (measured over
        # JSON-RPC on res.partner: depth 3 -> 0.5 MiB, depth 7 -> 11 MiB,
        # depth 9 -> 47 MiB), and nothing refused the call. Clamp rather than
        # raise: enterprise overrides pass `depth` straight through, and the
        # only legitimate callers use the default.
        depth = min(depth, FIELDS_RECURSION_LIMIT)
        # `model` is caller-supplied over RPC and nothing checked it. Defence
        # in depth rather than a closed hole: measured, the tree is *narrower*
        # than the `fields_get` it wraps (14 fields vs 21 on ir.mail_server for
        # a plain internal user, since readonly and magic columns are dropped),
        # so it discloses nothing that model's own `fields_get` does not
        # already hand out. What it adds is reach -- one call walks ~49
        # comodels, three levels deep. Checked on the entry model only: the
        # recursion below legitimately descends into comodels a user may not
        # read directly but must still be able to map onto.
        self._check_model_name(model)
        self.env[model].check_access("read")
        return self._get_fields_tree(model, depth)

    @api.model
    def _check_model_name(self, model):
        """Refuse a model name that names nothing, with a message.

        ``res_model`` is a plain ``Char`` the client fills in at ``create``
        time and ``model`` here is an RPC argument, so both are caller-supplied
        and neither need name a real model. ``self.env[<not a model>]`` raises
        ``KeyError``, which no entry point of this module catches: an import
        record carrying a typo -- or none at all, since the field is not
        ``required`` -- answered ``parse_preview`` with an HTTP 500 and a bare
        ``KeyError: 'nope.nope'``.

        :raises UserError: rather than :class:`ImportValidationError`, which
            the client renders as a per-column import message. A record whose
            target model does not exist is not a mapping problem; nothing about
            it is fixable from the mapping screen.
        """
        if not model or model not in self.env:
            raise UserError(
                _(
                    "Cannot import into %(model)s: no such model.",
                    model=model or _("(none)"),
                )
            )

    def _expand_properties_fields(self, Model, model_fields):
        """Add each Properties field's sub-columns to ``model_fields`` in place.

        A Properties field holds user-defined sub-columns whose definitions live
        on a *parent* record, so ``fields_get`` never reports them and the
        mapper would have nothing to offer for them. One pseudo-field is added
        per definition found on a non-archived parent, keyed ``<field>.<name>``.

        :param Model: the model being imported into
        :param dict model_fields: ``fields_get`` output, mutated in place
        """
        for name, field in dict(model_fields).items():
            # `not in 'properties'` was a substring test against the *string*
            # "properties", not a type comparison: it happened to behave for
            # today's field types only because none of them is a substring of
            # "properties".
            if field["type"] != "properties":
                continue
            definition_record = field["definition_record"]
            definition_record_field = field["definition_record_field"]

            target_model = Model.env[Model._fields[definition_record].comodel_name]

            # ignore if you cannot access to the target model or the field definition
            if not target_model.has_access("read"):
                continue
            if not target_model._has_field_access(
                target_model._fields[definition_record_field], "read"
            ):
                continue

            # Do not take into account the definition of archived parents,
            # we do not import archived records most of the time.
            definition_records = target_model.search_fetch(  # noqa: E8507 - one query per properties field of the import
                [(definition_record_field, "!=", False)],
                [definition_record_field, "display_name"],
                order="id",  # Avoid complex order
            )

            for record in definition_records:
                for definition in record[definition_record_field]:
                    definition_type = definition["type"]
                    if definition_type == "separator" or (
                        definition_type in ("many2one", "many2many")
                        and definition.get("comodel") not in Model.env
                    ):
                        continue
                    id_field = f"{name}.{definition['name']}"
                    model_fields[id_field] = {
                        "type": definition_type,
                        "string": _(
                            "%(property_string)s (%(parent_name)s)",
                            property_string=definition["string"],
                            parent_name=record.display_name,
                        ),
                    }
                    if definition_type in ("many2one", "many2many"):
                        model_fields[id_field]["relation"] = definition["comodel"]
                    elif definition_type == "selection":
                        model_fields[id_field]["selection"] = (
                            definition.get("selection") or []
                        )

    def _get_field_tree_node(self, model, name, field, depth):
        """One importable-field node, with the subtree of a relational field.

        :param str model: the model the field belongs to
        :param str name: technical field name
        :param dict field: its ``fields_get`` entry
        :param int depth: remaining recursion budget, see :meth:`get_fields_tree`
        :rtype: dict
        """
        field_value = {
            "id": name,
            "name": name,
            "string": field["string"],
            # fields_get does not always return a "required" key
            "required": bool(field.get("required")),
            "fields": [],
            "type": field["type"],
            "model_name": model,
        }

        if field["type"] == "selection":
            # A Properties sub-column is not a field of `model`, so the
            # client cannot recover its selection with a second fields_get.
            field_value["selection"] = field.get("selection") or []

        if field["type"] in ("many2many", "many2one"):
            field_value["fields"] = [
                dict(
                    field_value,
                    model_name=field["relation"],
                    name="id",
                    string=_("External ID"),
                    type="id",
                ),
                dict(
                    field_value,
                    model_name=field["relation"],
                    name=".id",
                    string=_("Database ID"),
                    type="id",
                ),
            ]
            field_value["comodel_name"] = field["relation"]
        elif field["type"] == "one2many":
            field_value["fields"] = self._get_fields_tree(
                field["relation"], depth=depth - 1
            )
            if self.env.user.has_group("base.group_no_one"):
                field_value["fields"].append(
                    dict(
                        field_value,
                        model_name=field["relation"],
                        fields=[],
                        name=".id",
                        string=_("Database ID"),
                        type="id",
                    )
                )
            field_value["comodel_name"] = field["relation"]

        return field_value

    def _get_fields_tree(self, model, depth):
        """Recursive body of :meth:`get_fields_tree`, without its access
        check -- see the note there on why the check is not repeated per level.
        """
        Model = self.env[model]
        importable_fields = [
            {
                "id": "id",
                "name": "id",
                "string": _("External ID"),
                "required": False,
                "fields": [],
                "type": "id",
                "model_name": model,
            }
        ]
        if not depth:
            return importable_fields

        model_fields = Model.fields_get(
            attributes=[
                "string",
                "required",
                "type",
                "readonly",
                "relation",
                "selection",
                "definition_record",
                "definition_record_field",
            ]
        )
        self._expand_properties_fields(Model, model_fields)

        for name, field in model_fields.items():
            if name in models.MAGIC_COLUMNS or field.get("readonly"):
                continue
            importable_fields.append(
                self._get_field_tree_node(model, name, field, depth)
            )

        return importable_fields

    def _filter_fields_by_types(self, model_fields_tree, header_types):
        """Narrow ``model_fields_tree`` to the fields worth fuzzy-matching a
        column whose values look like ``header_types``.

        **Scalar** fields are kept only if their type is in ``header_types``.
        **Relational** fields (anything carrying subfields) are kept
        unconditionally, and filtered recursively inside. That is deliberate,
        not an oversight: a column of integers can perfectly well be a
        many2one addressed by database id, so its type says nothing about
        whether the header names a relation. The consequence is worth knowing
        before "tightening" this -- for ``header_types=['integer']`` on
        res.partner it keeps 24 of 56 fields, 22 of them relational -- because
        moving the type test out of the ``elif`` would silently change every
        suggestion the module makes.

        :param list[dict] model_fields_tree: Contains recursively all the importable fields of
            the target model. Generated in :meth:`get_fields_tree`.
        :param list header_types: Contains the extracted fields types of the current header.
            Generated in :meth:`_extract_header_types`.
        """
        # 'all' is the sentinel `_extract_header_types` returns for a column
        # whose preview rows are all empty: nothing is known about it, so every
        # field is a candidate. Without this case the filter kept only fields
        # that have subfields -- i.e. only relational ones -- so an empty column
        # silently lost every fuzzy suggestion it would otherwise have got
        # (header "Functon" matched `function` when the column had data, and
        # matched nothing at all when it did not).
        if "all" in header_types:
            return model_fields_tree

        most_likely_fields_tree = []
        for field in model_fields_tree:
            subfields = field.get("fields")
            if subfields:
                filtered_field = dict(field)  # Avoid modifying fields.
                filtered_field["fields"] = self._filter_fields_by_types(
                    subfields, header_types
                )
                most_likely_fields_tree.append(filtered_field)
            elif field.get("type") in header_types:
                most_likely_fields_tree.append(field)
        return most_likely_fields_tree

    @api.model
    def _normalize_row_window_options(self, options):
        """Coerce ``skip`` and ``limit`` to the non-negative integers every
        consumer below assumes, in place.

        Both reach the server as whatever the client's input produced, and both
        inputs are plain free-text ``<input>`` elements in the batch panel -- so
        a typo is an ordinary user action here, not a crafted call. Neither was
        checked, and each bad value failed differently and badly:

        * ``limit="abc"`` -- ``num_rows > "abc"`` in :meth:`parse_preview` and
          ``limit >= len(data)`` in :meth:`_batch_window` both raise
          ``TypeError``. ``execute_import`` catches only
          :class:`ImportValidationError`, so it left as an HTTP 500;
          ``parse_preview`` caught it and told the user the *file* could not be
          read, which is a lie about a perfectly good file.
        * ``limit=-5`` -- ``IndexError`` out of the row window, again a 500.
        * ``skip=-2`` -- no error at all, which is the worst of the three.
          ``data[-2:]`` is a legal slice, so the import silently ran on the
          *last* two rows of the file and reported success. The UI reaches this:
          "Start at line" sends ``value - 1``, and the string ``"0"`` is truthy
          in JavaScript, so entering 0 sends ``skip=-1`` and imports the last
          row alone.

        A numeric string is accepted and coerced rather than refused: the two
        inputs are untyped, so the client already sends one for some edits, and
        refusing it would break a round trip that works today.
        """
        for name in ("skip", "limit"):
            if name not in options:
                continue
            value = options[name]
            # "No value" means different things to the two options, so neither
            # may be folded into the other.
            #
            # `skip` unset is 0, and normalising it is a fix: `[""] * None` in
            # `_record_names` raised.
            #
            # `limit` unset is **None**, the only spelling `load` reads as "no
            # limit" (it substitutes `float("inf")`). Every other falsy value
            # lands in `index < limit` as itself, and this module's own
            # `_batch_window` disagrees with `load` about all of them -- it
            # treats a falsy limit as "no batching" and hands over every row,
            # while `load` stops at 0 and imports none. Measured through
            # `load`: `_import_limit=None` takes 4 of 4 rows, `0` and `False`
            # take none while reporting success and `nextrow=0`, so the client
            # is told the import finished; `""` raises `TypeError: '<' not
            # supported between instances of 'int' and 'str'` and leaves as an
            # HTTP 500. Resolving that in `_batch_window`'s favour is what the
            # one already-stated intent in this module says: falsy means no
            # limit.
            if not value:
                options[name] = 0 if name == "skip" else None
                continue
            if isinstance(value, bool) or not isinstance(value, int | str):
                raise ImportValidationError(self._bad_row_window_message(name, value))
            try:
                coerced = int(value)
            except ValueError:
                raise ImportValidationError(
                    self._bad_row_window_message(name, value)
                ) from None
            if coerced < 0:
                raise ImportValidationError(self._bad_row_window_message(name, value))
            options[name] = coerced
        return options

    @api.model
    def _bad_row_window_message(self, name, value):
        labels = {"skip": _("Start at line"), "limit": _("Batch limit")}
        return _(
            "%(option)s must be a whole number of rows, not %(value)s.",
            option=labels[name],
            value=value,
        )

    def _read_file(self, options):
        """The file's non-empty rows, parsed once per (content, read options).

        See :class:`_ParsedFileCache` for why this is memoized at all and why
        the key is the file's content. The options a reader *writes* are
        replayed on a hit, so a caller cannot tell a hit from a miss except by
        how long it took.

        :param dict options: reading options (quoting, separator, ...)
        :returns: the file's non-empty rows
        :rtype: list[list]
        """
        self.check_singleton()

        key = self._parsed_file_key(options)
        hit = PARSED_FILE_CACHE.get(key)
        if hit is not None:
            rows, outputs = hit
            options.update(_copy_option_outputs(outputs))
            return list(rows)

        before = {name: options.get(name) for name in PARSE_OPTION_OUTPUTS}
        rows = self._read_file_uncached(options)
        outputs = {
            name: options[name]
            for name in PARSE_OPTION_OUTPUTS
            if name in options and options[name] != before[name]
        }
        # Copied on the way in as well as on the way out. `sheets` is a list,
        # and the reader leaves the very object it built in the caller's
        # `options` -- storing that reference lets a caller that appends to its
        # own `options["sheets"]` rewrite the cached entry, so every later hit
        # reports a sheet the workbook does not have. Verified: without this,
        # appending to `options["sheets"]` after a miss showed up in the next
        # read.
        PARSED_FILE_CACHE.set(key, rows, _copy_option_outputs(outputs))
        return list(rows)

    def _parsed_file_key(self, options):
        """What makes two reads of this file interchangeable.

        The dispatch in :meth:`_read_file_uncached` is driven by the content,
        the declared mimetype and the name, so all three belong in the key
        alongside the options the readers consume.
        """
        return (
            hashlib.blake2b(self.file or b"", digest_size=16).digest(),
            self.file_name or "",
            self.file_type or "",
            tuple(options.get(name) for name in PARSE_OPTION_KEYS),
        )

    def _read_file_uncached(self, options):
        """Dispatch to the reader for this file's format, deduced from its
        content, its declared mimetype, or its extension (in that order).

        :param dict options: reading options (quoting, separator, ...)
        :returns: the file's non-empty rows
        :rtype: list[list]
        """
        # guess mimetype from file content
        mimetype = guess_mimetype(self.file or b"")
        extensions_to_try = [
            (MIMETYPE_TO_READER.get(mimetype), f"guessed using mimetype {mimetype!r}"),
            (
                MIMETYPE_TO_READER.get(self.file_type),
                f"decided from user-provided mimetype {self.file_type!r}",
            ),
        ]
        # fallback on file extensions as mime types can be unreliable (e.g.
        # software setting incorrect mime types, or non-installed software
        # leading to browser not sending mime types)
        if self.file_name:
            ext = Path(self.file_name).suffix
            extensions_to_try.append(
                (ext.removeprefix(".").lower(), f"decided from file extension {ext!r}")
            )

        e = None
        requires = None
        requires_extension = None
        tried_extensions = set()
        for file_extension, guess_message in extensions_to_try:
            if not file_extension or file_extension in tried_extensions:
                continue
            tried_extensions.add(file_extension)
            # Allow-list lookup, never `getattr(self, '_read_' + <user input>)`:
            # see EXTENSION_TO_READER for what that used to make reachable.
            handler_name = EXTENSION_TO_READER.get(file_extension)
            if not handler_name:
                continue
            try:
                return getattr(self, handler_name)(options)
            except ImportError as exc:
                # exc.name_from attribute is present as of python 3.12
                requires = str(getattr(exc, "name_from", None) or exc.name)
                requires_extension = file_extension
            except ImportValidationError, UserError, ValueError:
                raise
            except Exception as exc:
                e = _prepare_read_file_error(
                    exc,
                    f"Unable to read file {self.file_name or '<unknown>'!r} as {file_extension!r} ({guess_message}).",
                )

        if e is not None:
            raise e

        if requires:
            raise UserError(
                _(
                    'Unable to load "%(extension)s" file: requires Python module "%(modname)s"',
                    extension=requires_extension,
                    modname=requires,
                )
            )
        raise UserError(
            _(
                'Unsupported file format "%(file_type)s", import only supports %(supported)s',
                file_type=self.file_type or (self.file_name or ""),
                supported=", ".join(sorted(EXTENSION_TO_READER)),
            )
        )

    def _check_csv_quoting(self, options):
        quoting = options.setdefault("quoting", '"')
        if not isinstance(quoting, str) or len(quoting) != 1:
            raise ImportValidationError(
                _(
                    "Error while importing records: Text Delimiter should be a single character."
                )
            )
        return quoting

    def _decode_csv_text(self, csv_data, options):
        encoding = options.get("encoding")
        encoding_guessed = not encoding
        if encoding_guessed:
            encoding = guess_encoding(csv_data)
            if not encoding:
                raise ImportValidationError(
                    _(
                        "Could not detect the file's encoding, please select it manually."
                    )
                )
            options["encoding"] = encoding

        try:
            return decode(csv_data, encoding)
        except UnicodeDecodeError as exc:
            if encoding_guessed:
                msg = _(
                    "There was an issue decoding the file using encoding “%s”.\nThis encoding was automatically detected.",
                    encoding,
                )
            else:
                msg = _(
                    "There was an issue decoding the file using encoding “%s”.\nThis encoding was manually selected.",
                    encoding,
                )
            raise ImportValidationError(msg) from exc

    def _guess_csv_separator(self, csv_text, quoting, options):
        for candidate in (
            ",",
            ";",
            "\t",
            " ",
            "|",
            unicodedata.lookup("unit separator"),
        ):
            it = csv.reader(
                io.StringIO(csv_text), quotechar=quoting, delimiter=candidate
            )
            w = None
            for row in itertools.islice(it, SEPARATOR_SNIFF_ROWS):
                width = len(row)
                if w is None:
                    w = width
                if width == 1 or width != w:
                    break  # next candidate
            else:  # nobreak
                options["separator"] = candidate
                return candidate
        return ","

    def _read_xls(self, options):
        return read_xls_rows(self.file or b"", options)

    def _read_xlsx(self, options):
        return read_xlsx_rows(self.file or b"", options)

    def _read_ods(self, options):
        return read_ods_rows(self.file or b"", options)

    def _read_csv(self, options):
        quoting = self._check_csv_quoting(options)

        csv_data = self.file or b""
        if not csv_data:
            return []

        csv_text = self._decode_csv_text(csv_data, options)
        separator = options.get("separator") or self._guess_csv_separator(
            csv_text, quoting, options
        )

        csv_iterator = csv.reader(
            io.StringIO(csv_text), quotechar=quoting, delimiter=separator
        )

        return [row for row in csv_iterator if any(x for x in row if x.strip())]

    @api.model
    def _match_float_separators(self, preview_values, options):
        thousand_separator = decimal_separator = False
        currency_symbols = None
        for val in preview_values:
            val = val.strip()
            if not val:
                continue
            if currency_symbols is None:
                currency_symbols = self._currency_symbols()
            val = self._remove_currency_symbol(val, currency_symbols)
            if not val:
                return False
            if options.get("float_thousand_separator") and options.get(
                "float_decimal_separator"
            ):
                if options["float_decimal_separator"] == "." and val.count(".") > 1:
                    return False
                val = val.replace(options["float_thousand_separator"], "").replace(
                    options["float_decimal_separator"], "."
                )
            elif val.count(".") > 1:
                options["float_thousand_separator"] = "."
                options["float_decimal_separator"] = ","
            elif val.count(",") > 1:
                options["float_thousand_separator"] = ","
                options["float_decimal_separator"] = "."
            elif val.find(".") > val.find(","):
                thousand_separator = ","
                decimal_separator = "."
            elif val.find(",") > val.find("."):
                thousand_separator = "."
                decimal_separator = ","
        if thousand_separator and not options.get("float_decimal_separator"):
            options["float_thousand_separator"] = thousand_separator
            options["float_decimal_separator"] = decimal_separator
        return True

    def _match_string_column_types(self, preview_values, options):
        values = set(preview_values)
        if values == {""}:
            return ["all"]

        if all(v.startswith("__export__") for v in values):
            return ["id", "many2many", "many2one", "one2many"]

        if all(_is_integer_literal(v) for v in values if v):
            field_type = ["integer", "float", "monetary"]
            if {"0", "1", ""}.issuperset(values):
                field_type.append("boolean")
            return field_type

        if all(
            val.lower() in ("true", "false", "t", "f", "") for val in preview_values
        ):
            return ["boolean"]

        if self._match_float_separators(preview_values, options):
            # Allow float to be mapped on a text field.
            return ["float", "monetary"]

        return None

    def _extract_header_types(self, preview_values, options):
        if not preview_values:
            return ["all"]

        if all(isinstance(v, str) for v in preview_values):
            preview_values = [v.strip() for v in preview_values]
            field_types = self._match_string_column_types(preview_values, options)
            if field_types:
                return field_types

        if _is_native_date_column(preview_values):
            return ["date", "datetime"]

        results = self._try_match_date_time(preview_values, options)
        if results:
            return results

        return ["text", "char", "binary", "selection", "html", "tags"]

    def _try_match_date_time(self, preview_values, options):
        date_patterns = [options["date_format"]] if options.get("date_format") else []
        user_date_format = (
            self.env["res.lang"]._get_data(code=self.env.user.lang).date_format
        )
        if user_date_format:
            try:
                to_re(user_date_format)
                date_patterns.append(user_date_format)
            except KeyError:
                pass
        date_patterns.extend(DATE_PATTERNS)
        match = get_matching_pattern(date_patterns, preview_values)
        if match:
            options["date_format"] = match
            return ["date", "datetime"]

        datetime_patterns = (
            [options["datetime_format"]] if options.get("datetime_format") else []
        )
        datetime_patterns.extend(
            "%s %s" % (d, t) for d in date_patterns for t in TIME_PATTERNS
        )
        match = get_matching_pattern(datetime_patterns, preview_values)
        if match:
            options["datetime_format"] = match
            return ["datetime"]

        return []

    @api.model
    def _extract_headers_types(self, headers, preview, options):
        headers_types = {}
        for column_index, header_name in enumerate(headers):
            preview_values = [
                record[column_index] if column_index < len(record) else ""
                for record in preview
            ]
            type_field = self._extract_header_types(preview_values, options)
            headers_types[(column_index, header_name)] = type_field
        return headers_types

    def _get_saved_mapping_suggestion(self, header, fields_tree, mapping_fields):
        mapping_field_name = mapping_fields.get(_normalize_column_name(header))
        if mapping_field_name and self._mapping_path_exists(
            mapping_field_name, fields_tree
        ):
            return {
                "field_path": mapping_field_name.split("/"),
                "distance": -1,  # Trick to force to keep that match during mapping deduplication.
            }
        return {}

    def _get_exact_field_match(self, header, fields_tree, field_strings_en):
        for field in fields_tree:
            fname = field["name"]
            if header.casefold() == fname.casefold():
                return field
            if header.casefold() == field["string"].casefold():
                return field
            strings_en = field_strings_en(field["model_name"])
            if (
                fname in strings_en
                and header.casefold() == strings_en[fname].casefold()
            ):
                return field
        return None

    def _get_fuzzy_field_match(
        self, header, fields_tree, header_types, field_strings_en
    ):
        filtered_fields = self._filter_fields_by_types(fields_tree, header_types)
        if not filtered_fields:
            return {}

        min_dist = 1
        min_dist_field = False
        for field in filtered_fields:
            fname = field["name"]
            distances = [
                self._get_distance(header.casefold(), fname.casefold()),
                self._get_distance(header.casefold(), field["string"].casefold()),
            ]

            if field_string_en := field_strings_en(field["model_name"]).get(fname):
                distances.append(
                    self._get_distance(header.casefold(), field_string_en.casefold()),
                )

            current_field_dist = min(distances)
            if current_field_dist < min_dist:
                min_dist_field = fname
                min_dist = current_field_dist

        if min_dist < self.FUZZY_MATCH_DISTANCE:
            return {"field_path": [min_dist_field], "distance": min_dist}

        return {}

    def _get_relational_mapping_suggestion(self, header, fields_tree, header_types):
        field_path = []
        subfields_tree = fields_tree
        for sub_header in header.split("/"):
            match = self._get_mapping_suggestion(
                sub_header.strip(), subfields_tree, header_types, {}
            )
            if not match:
                return {}
            field_name = match["field_path"][0]
            subfields_tree = next(
                item["fields"] for item in subfields_tree if item["name"] == field_name
            )
            field_path.append(field_name)
        return {"field_path": field_path}

    def _get_mapping_suggestion(
        self, header, fields_tree, header_types, mapping_fields
    ):
        if not fields_tree:
            return {}

        if saved_match := self._get_saved_mapping_suggestion(
            header, fields_tree, mapping_fields
        ):
            return saved_match

        if "/" in header:
            return self._get_relational_mapping_suggestion(
                header, fields_tree, header_types
            )

        field_strings_en = self._get_field_strings_en()

        if field := self._get_exact_field_match(header, fields_tree, field_strings_en):
            return {"field_path": [field["name"]], "distance": 0}

        return self._get_fuzzy_field_match(
            header, fields_tree, header_types, field_strings_en
        )

    def _get_field_strings_en(self):
        IrModelFieldsUs = self.with_context(lang="en_US").env["ir.model.fields"]

        @functools.cache
        def get_field_string(model_name):
            return IrModelFieldsUs.get_field_string(model_name)

        return get_field_string

    def _mapping_path_exists(self, field_path, fields_tree):
        subtree = fields_tree
        for name in field_path.split("/"):
            match = next((f for f in subtree if f["name"] == name), None)
            if match is None:
                return False
            subtree = match.get("fields") or []
        return True

    def _get_distance(self, a, b):
        return 1 - difflib.SequenceMatcher(None, a, b).ratio()

    def _get_mapping_suggestions(self, headers, header_types, fields_tree):
        mapping_suggestions = {}
        mapping_records = self.env["base_import.mapping"].search_read(
            [("res_model", "=", self.res_model)], ["column_name", "field_name"]
        )
        mapping_fields = {
            _normalize_column_name(rec["column_name"]): rec["field_name"]
            for rec in mapping_records
        }
        for index, header in enumerate(headers):
            match_field = self._get_mapping_suggestion(
                header, fields_tree, header_types[(index, header)], mapping_fields
            )
            mapping_suggestions[(index, header)] = match_field or None

        self._deduplicate_mapping_suggestions(mapping_suggestions)
        return mapping_suggestions

    def _deduplicate_mapping_suggestions(self, mapping_suggestions):
        min_dist_per_field = {}
        headers_to_keep = []
        for header, suggestion in mapping_suggestions.items():
            if suggestion is None or len(suggestion["field_path"]) > 1:
                headers_to_keep.append(header)
                continue

            field_name = suggestion["field_path"][0]
            field_distance = suggestion["distance"]

            best_distance, _best_header = min_dist_per_field.get(field_name, (1, None))
            if field_distance < best_distance:
                min_dist_per_field[field_name] = (field_distance, header)

        headers_to_keep += [value[1] for value in min_dist_per_field.values()]
        for header in mapping_suggestions.keys() - headers_to_keep:
            del mapping_suggestions[header]

    def _get_preview_matches(self, headers, header_types, fields_tree, options):
        matches = {}
        if options.get("keep_matches") and options.get("fields"):
            for index, match in enumerate(options.get("fields", [])):
                if match:
                    matches[index] = match.split("/")
        elif options.get("has_headers"):
            suggestions = self._get_mapping_suggestions(
                headers, header_types, fields_tree
            )
            matches = {
                header_key[0]: suggestion["field_path"]
                for header_key, suggestion in suggestions.items()
                if suggestion
            }
        return matches

    def _is_advanced_mode(self, headers, matches, options):
        if options.get("keep_matches"):
            return options.get("advanced")
        has_relational_header = any(
            len(models.fix_import_export_id_paths(col)) > 1 for col in headers
        )
        has_relational_match = any(
            len(match) > 1 for match in matches.values() if match
        )
        return has_relational_header or has_relational_match

    def _get_preview_error(self, error):
        if isinstance(
            error, ImportValidationError | UserError | ValueError | csv.Error
        ):
            message = str(error)
        else:
            _logger.error(
                "Unexpected error while parsing the import preview", exc_info=error
            )
            message = _(
                "The file could not be read. Please check the format options, or contact your administrator if the problem persists."
            )
        preview = None
        if self.file_type == "text/csv" and self.file:
            preview = self.file[:ERROR_PREVIEW_BYTES].decode("iso-8859-1")
        return {
            "error": message,
            "preview": preview,
        }

    def _get_preview(self, options, count, fields_tree):
        self._normalize_row_window_options(options)
        data_rows = self._read_file(options)
        if not data_rows:
            raise ImportValidationError(_("Import file has no content or is corrupt"))

        preview = data_rows[:count]

        if options.get("has_headers") and preview:
            headers = preview.pop(0)
            header_types = self._extract_headers_types(headers, preview, options)
        else:
            header_types, headers = {}, []

        matches = self._get_preview_matches(headers, header_types, fields_tree, options)
        advanced_mode = self._is_advanced_mode(headers, matches, options)
        column_example = self._prepare_column_examples(headers, preview, options)

        num_rows = len(data_rows) - (1 if headers else 0)
        batch_cutoff = options.get("limit")
        batch = bool(batch_cutoff) and num_rows > batch_cutoff

        return {
            "fields": fields_tree,
            "matches": matches or False,
            "headers": headers or False,
            "header_types": list(header_types.values()) or False,
            "preview": column_example,
            "options": options,
            "advanced_mode": advanced_mode,
            "debug": self.env.user.has_group("base.group_no_one"),
            "batch": batch,
            "num_rows": num_rows,
        }

    def parse_preview(self, options, count=10):
        self.check_singleton()
        self._check_model_name(self.res_model)
        fields_tree = self.get_fields_tree(self.res_model)
        try:
            return self._get_preview(options, count, fields_tree)
        except Exception as error:
            return self._get_preview_error(error)

    def _prepare_column_examples(self, headers, preview, options):
        column_count = max(len(headers), *(len(row) for row in preview or [[]]))
        datetime_format = (
            options.get("datetime_format") or DEFAULT_SERVER_DATETIME_FORMAT
        )
        date_format = options.get("date_format") or DEFAULT_SERVER_DATE_FORMAT

        column_examples = []
        for column_index in range(column_count):
            values = []
            for record in preview:
                value = record[column_index] if column_index < len(record) else ""
                if value and isinstance(value, str):
                    values.append(
                        "%s%s" % (value[:50], "..." if len(value) > 50 else "")
                    )
                elif isinstance(value, datetime.datetime):
                    values.append(value.strftime(datetime_format))
                elif isinstance(value, datetime.date):
                    values.append(value.strftime(date_format))
                if len(values) == 5:
                    break
            column_examples.append(values or [""])
        return column_examples

    @api.model
    def _check_field_mapping(self, fields):
        for position, field in enumerate(fields, start=1):
            if field and not isinstance(field, str):
                raise ImportValidationError(
                    _(
                        "Column %(column)s is not mapped to a field name.",
                        column=position,
                    )
                )

    def _map_import_rows(
        self, rows_to_import, mapper, max_index, title_row_entries, options
    ):
        data = []
        for row_number, row in enumerate(
            rows_to_import, start=2 if options.get("has_headers") else 1
        ):
            if len(row) <= max_index:
                raise ImportValidationError(
                    _(
                        "Error while importing records: all rows should be of the same size, "
                        "but the title row has %(title_row_entries)d entries while row "
                        "%(row_number)d has %(row_entries)d. You may need to change the "
                        "separator character.",
                        title_row_entries=title_row_entries,
                        row_number=row_number,
                        row_entries=len(row),
                    )
                )
            mapped = list(mapper(row))
            if any(mapped):
                data.append(mapped)
        return data

    def _convert_import_data(
        self,
        fields: Sequence[str | bool],
        options,
    ) -> tuple[
        list[list[str]],  # data
        list[str],  # fields, without the bool items
    ]:
        self._check_field_mapping(fields)
        indices = [index for index, field in enumerate(fields) if field]
        if not indices:
            raise ImportValidationError(
                _("You must configure at least one field to import")
            )
        if len(indices) == 1:

            def mapper(row):
                return [row[indices[0]]]
        else:
            mapper = operator.itemgetter(*indices)
        import_fields = [f for f in fields if f]

        rows_to_import = self._read_file(options)
        if not rows_to_import:
            raise ImportValidationError(_("Import file has no content or is corrupt"))
        if len(rows_to_import[0]) != len(fields):
            raise ImportValidationError(
                _(
                    "Error while importing records: all rows should be of the same size, but the title row has %(title_row_entries)d entries while the first row has %(first_row_entries)d. You may need to change the separator character.",
                    title_row_entries=len(fields),
                    first_row_entries=len(rows_to_import[0]),
                ),
            )

        if options.get("has_headers"):
            rows_to_import = rows_to_import[1:]

        data = self._map_import_rows(
            rows_to_import, mapper, indices[-1], len(fields), options
        )

        return data[options.get("skip") or 0 :], import_fields

    def _batch_window(self, import_fields, data, limit):
        if not limit or limit >= len(data):
            return len(data)

        continuation = self._continuation_rows(import_fields, data)
        window = limit
        while window < len(data) and continuation[window]:
            window += 1
        return window

    def _continuation_rows(self, import_fields, data):
        model = self.env[self.res_model]
        o2m_indexes, other_indexes = [], []
        for index, path in enumerate(import_fields):
            field = model._fields.get(path.split("/")[0])
            (
                o2m_indexes
                if field is not None and field.type == "one2many"
                else other_indexes
            ).append(index)

        if not o2m_indexes:
            return [False] * len(data)

        return [
            bool(
                index
                and any(row[i] for i in o2m_indexes if i < len(row))
                and not any(row[i] for i in other_indexes if i < len(row))
            )
            for index, row in enumerate(data)
        ]

    @api.model
    def _remove_currency_symbol(self, value, currency_symbols=None):
        if currency_symbols is None:
            currency_symbols = _StoredCurrencySymbols(self.env)
        number = strip_currency_symbol(value, currency_symbols)
        return False if number is None else number

    @api.model
    def _currency_symbols(self):
        symbols = (
            self.env["res.currency"]
            .with_context(active_test=False)
            .search([])
            .mapped("symbol")
        )
        return {s for s in symbols if s}

    @api.model
    def _parse_float_from_data(self, data, index, name, options):
        currency_symbols = self._currency_symbols()
        for line in data:
            line[index] = self._stringify_date_like_objects(
                line[index], options, trim=True
            )
            if not line[index]:
                continue
            thousand_separator, decimal_separator = self._infer_separators(
                line[index], options
            )

            if "E" in line[index] or "e" in line[index]:
                tmp_value = line[index].replace(thousand_separator, ".")
                try:
                    tmp_value = f"{float(tmp_value):f}"
                    line[index] = tmp_value
                    thousand_separator = " "
                except ValueError:
                    pass

            line[index] = (
                line[index]
                .replace(thousand_separator, "")
                .replace(decimal_separator, ".")
            )
            old_value = line[index]
            line[index] = self._remove_currency_symbol(line[index], currency_symbols)
            if line[index] is False:
                raise ImportValidationError(
                    _(
                        "Column %(column)s contains incorrect values (value: %(value)s)",
                        column=name,
                        value=old_value,
                    ),
                    field=name,
                )

    def _infer_separators(self, value, options):
        """How ``value`` groups and points its digits, per :func:`infer_separators`."""
        return infer_separators(
            value,
            options.get("float_thousand_separator", " "),
            options.get("float_decimal_separator", "."),
        )

    def _parse_import_data(self, data, import_fields, options):
        path_models = self._check_import_paths(import_fields)
        for index, path in enumerate(import_fields):
            field = self._resolve_import_path(path, path_models)
            if field is None:
                continue
            if field.type in ("date", "datetime"):
                self._parse_date_from_data(data, index, path, field.type, options)
            elif field.type in ("float", "monetary"):
                self._parse_float_from_data(data, index, path, options)
            elif field.type == "binary" and field.attachment:
                self._parse_binary_from_data(data, index, path, options)
        return data

    def _resolve_import_path(self, path, path_models=None):
        if path_models is not None and path in path_models:
            model = path_models[path]
        else:
            model = self._resolve_path_model(path)
        if not model:
            return None
        return self.env[model]._fields.get(path.split("/")[-1].split(".")[0])

    def _resolve_path_model(self, path):
        model = self.res_model
        for segment in path.split("/")[:-1]:
            if model not in self.env:
                return None
            name, _, property_name = segment.partition(".")
            parent = self.env[model]._fields.get(name)
            if parent is None:
                return None
            if parent.type == "properties":
                return "" if property_name else None
            if not parent.comodel_name:
                return None
            model = parent.comodel_name
        return model if model in self.env else None

    def _check_import_paths(self, import_fields):
        path_models = {}
        for path in import_fields:
            segments = path.split("/")
            if len(segments) == 1:
                continue
            model = self._resolve_path_model(path)
            path_models[path] = model
            if model is None:
                raise ImportValidationError(
                    _(
                        "Column %(column)s cannot be imported: %(path)s is not a "
                        "relation on model %(model)s, so it has no sub-fields.",
                        column=path,
                        path="/".join(segments[:-1]),
                        model=self.res_model,
                    ),
                    field=path,
                )
        return path_models

    def _parse_binary_from_data(self, data, index, name, options):
        with self.env["ir.egress"].session(
            purpose="import_url", max_bytes=None
        ) as session:
            session.stream = True

            for num, line in enumerate(data):
                if isinstance(line[index], (datetime.date, datetime.datetime)):
                    line[index] = self._stringify_date_like_objects(
                        line[index], options
                    )
                if re.match(config.get("import_url_regex"), line[index]):
                    if not self.env.user._can_import_remote_urls():
                        raise ImportValidationError(
                            _(
                                "You can not import file via URL, check with your administrator or support for the reason."
                            ),
                            field=name,
                            field_type="binary",
                        )
                    line[index] = self._import_file_by_url(
                        line[index], session, name, num
                    )
                elif "." in line[index]:
                    pass
                else:
                    try:
                        base64.b64decode(line[index], validate=True)
                    except ValueError as e:
                        raise ImportValidationError(
                            _(
                                "Found invalid image data, images should be imported as either URLs or base64-encoded data."
                            ),
                            field=name,
                            field_type="binary",
                        ) from e

    def _parse_date_from_data(self, data, index, name, field_type, options):
        dt = datetime.datetime
        fmt = (
            fields.Date.to_string if field_type == "date" else fields.Datetime.to_string
        )
        d_fmt = options.get("date_format") or DEFAULT_SERVER_DATE_FORMAT
        dt_fmt = options.get("datetime_format") or DEFAULT_SERVER_DATETIME_FORMAT
        for num, line in enumerate(data):
            if not line[index] or isinstance(line[index], datetime.date):
                continue

            v = line[index].strip()
            try:
                # first try parsing as a datetime if it's one
                if dt_fmt and field_type == "datetime":
                    try:
                        line[index] = fmt(dt.strptime(v, dt_fmt))
                        continue
                    except ValueError:
                        pass
                line[index] = fmt(dt.strptime(v, d_fmt))
            except ValueError as e:
                raise ImportValidationError(
                    _(
                        "Column %(column)s contains incorrect values. Error in line %(line)d: %(error)s",
                        column=name,
                        line=num + 1,
                        error=e,
                    ),
                    field=name,
                    field_type=field_type,
                ) from e
            except Exception as e:
                raise ImportValidationError(
                    _(
                        "Error Parsing Date [%(field)s:L%(line)d]: %(error)s",
                        field=name,
                        line=num + 1,
                        error=e,
                    ),
                    field=name,
                    field_type=field_type,
                ) from e

    def _import_file_by_url(self, url, session, field, line_number):
        assert re.match(config.get("import_url_regex"), url)
        maxsize = config.get("import_file_maxbytes")
        _logger.debug(
            "Trying to import file from URL: %s into field %s, at line %s",
            url,
            field,
            line_number,
        )
        try:
            response = session.get(url, timeout=config.get("import_file_timeout"))
            response.raise_for_status()

            if (
                response.headers.get("Content-Length")
                and int(response.headers["Content-Length"]) > maxsize
            ):
                raise ImportValidationError(
                    _("File size exceeds configured maximum (%s bytes)", maxsize),
                    field=field,
                )

            content = bytearray()
            for chunk in response.iter_content(DEFAULT_CHUNK_SIZE):
                content += chunk
                if len(content) > maxsize:
                    raise ImportValidationError(
                        _("File size exceeds configured maximum (%s bytes)", maxsize),
                        field=field,
                    )

            if not guess_mimetype(content).startswith("image/"):
                return base64.b64encode(content)

            image = Image.open(io.BytesIO(content))
            w, h = image.size
            if w * h > 42e6:  # Nokia Lumia 1020 photo resolution
                raise ImportValidationError(
                    _(
                        "Image size excessive, imported images must be smaller than 42 million pixel"
                    ),
                    field=field,
                )

            return base64.b64encode(content)
        except ImportValidationError:
            # Let the specific, already-actionable errors raised above (size caps,
            # image-resolution cap) reach the caller as-is: the generic handler
            # below used to re-wrap them into a "Could not retrieve URL" message,
            # losing both the specific text and the field/field_type routing used
            # by the client to attach the error to the right column (t24068 F2).
            raise
        except Exception as e:
            _logger.warning(e, exc_info=True)
            raise ImportValidationError(
                _(
                    "Could not retrieve URL: %(url)s [%(field_name)s: L%(line_number)d]: %(error)s"
                )
                % {
                    "url": url,
                    "field_name": field,
                    "line_number": line_number + 1,
                    "error": e,
                },
                field=field,
            ) from e

    @api.model
    def _stringify_date_like_objects(self, data, options, trim=False):
        # As imported string like datas might be automatically interpreted and imported as date/datetime
        # object by the spreedsheet a reconversion might be needed
        if isinstance(data, datetime.datetime):
            res = data.strftime(
                options.get("datetime_format") or DEFAULT_SERVER_DATETIME_FORMAT
            )
        elif isinstance(data, datetime.date):
            res = data.strftime(
                options.get("date_format") or DEFAULT_SERVER_DATE_FORMAT
            )
        else:
            res = data
        return res.strip() if trim else res

    def _merge_import_columns(self, import_fields, input_file_data, options):
        """Reduce the parsed rows to one value per mapped field.

        Collapses columns mapped more than once onto the same field, then
        substitutes fallback values for cells their field would refuse.

        :rtype: tuple[list[str], list[list]]
        """
        import_fields, merged_data = self.with_context(
            import_options=options
        )._handle_multi_mapping(import_fields, input_file_data)

        if options.get("fallback_values"):
            merged_data = self._handle_fallback_values(
                import_fields, merged_data, options["fallback_values"]
            )
        return import_fields, merged_data

    def _load_import_data(self, import_fields, merged_data, options, import_limit):
        """Hand the prepared rows to ``load`` on the target model.

        :param list import_fields: field paths, without holes
        :param list merged_data: the matching data matrix
        :param dict options: parsing options, ``limit`` popped off here
        :param import_limit: the ``limit`` read before the merge stages
        :rtype: dict
        """
        name_create_enabled_fields = options.pop("name_create_enabled_fields", {})
        options.pop("limit", None)
        model = self.env[self.res_model].with_context(
            import_file=True,
            name_create_enabled_fields=name_create_enabled_fields,
            import_set_empty_fields=options.get("import_set_empty_fields", []),
            import_skip_records=options.get("import_skip_records", []),
            _import_limit=import_limit,
        )
        return model.load(import_fields, merged_data)

    def _finalize_import_result(
        self, import_result, columns, fields, import_fields, merged_data, options
    ):
        """Post-process what ``load`` returned, in place.

        Saves the column mapping for next time, names the imported records and
        rebases ``nextrow`` onto the file the user uploaded rather than the
        batch ``load`` saw.
        """
        # Insert/Update mapping columns when import complete successfully
        if import_result["ids"] and options.get("has_headers"):
            self._save_column_mappings(columns, fields)

        import_result["name"] = self._record_names(import_fields, merged_data, options)

        # convert load's internal nextrow to the imported file's
        if import_result["nextrow"]:  # don't update if nextrow = 0 (= no nextrow)
            import_result["nextrow"] += options.get("skip", 0)

    def execute_import(self, fields, columns, options, dryrun=False):
        """Actual execution of the import

        :param fields: import mapping: maps each column to a field,
                       ``False`` for the columns to ignore
        :type fields: list(str|bool)
        :param columns: columns label
        :type columns: list(str|bool)
        :param dict options:
        :param bool dryrun: performs all import operations (and
                            validations) but rollbacks writes, allows
                            getting as much errors as possible without
                            the risk of clobbering the database.
        :returns: A list of errors. If the list is empty the import
                  executed fully and correctly. If the list is
                  non-empty it contains dicts with 3 keys:

                  ``type``
                    the type of error (``error|warning``)
                  ``message``
                    the error message associated with the error (a string)
                  ``record``
                    the data which failed to import (or ``false`` if that data
                    isn't available or provided)
        :rtype: dict(ids: list(int), messages: list({type, message, record}))
        """
        self.check_singleton()
        self._check_model_name(self.res_model)
        import_savepoint = self.env.cr.savepoint(flush=False)
        # `try/finally`, not just the `except ImportValidationError` below: the
        # savepoint used to be released only on the success path and on that
        # one expected exception, so anything else escaping the conversion
        # stages left the cursor inside a savepoint that was never closed --
        # `cr._savepoint_depth` grew and never came back down. HTTP discards
        # the transaction anyway, but automation and test callers do not, and
        # the leak long outlived the two crashes that used to reach it.
        released = False
        try:
            try:
                import_fields, input_file_data = self._prepare_batch_rows(
                    fields, options
                )
            except ImportValidationError as error:
                return {"messages": [error.__dict__]}
            import_limit = options.get("limit")

            _logger.info("importing %d rows...", len(input_file_data))

            binary_filenames = self._extract_binary_filenames(
                import_fields, input_file_data
            )
            import_fields, merged_data = self._merge_import_columns(
                import_fields, input_file_data, options
            )
            import_result = self._load_import_data(
                import_fields, merged_data, options, import_limit
            )
            _logger.info("done")

            # If transaction aborted, RELEASE SAVEPOINT is going to raise
            # an InternalError (ROLLBACK should work, maybe). Ignore that.
            with contextlib.suppress(psycopg.InternalError):
                import_savepoint.close(rollback=dryrun)
            released = True
            if dryrun:
                # cancel all changes done to the registry/ormcache
                # we need to clear the cache in case any created id was added to an ormcache and would be missing afterward
                self.pool.clear_all_caches()
                # don't propagate to other workers since it was rollbacked
                self.pool.reset_changes()

            self._finalize_import_result(
                import_result, columns, fields, import_fields, merged_data, options
            )
            if binary_filenames:
                import_result["binary_filenames"] = binary_filenames

            return import_result
        finally:
            if not released:
                with contextlib.suppress(psycopg.InternalError):
                    import_savepoint.close(rollback=True)

    def _prepare_batch_rows(self, fields, options):
        """The rows this batch will hand to ``load``, and the field paths that
        address them.

        Split out of :meth:`execute_import` because it is the one stretch of
        that method that can refuse the request: everything it calls raises
        :class:`ImportValidationError` for a caller mistake, and the caller
        turns that into a message on the import screen.

        :returns: ``(import_fields, rows)``
        :raises ImportValidationError: on any unusable option, mapping or row
        """
        # Normalised here rather than in the caller so that a bad option is
        # refused the same way an unusable mapping is, instead of escaping as
        # an HTTP 500.
        self._normalize_row_window_options(options)
        data, import_fields = self._convert_import_data(fields, options)
        # Parse date and float field
        data = self._parse_import_data(data, import_fields, options)
        # Only `load` used to honour the batch limit, so every stage below ran
        # over the whole remainder of the file on every batch. Trim to what this
        # batch can actually consume -- see _batch_window.
        #
        # Trim *after* parsing, not before: overrides of _parse_import_data
        # legitimately read the whole remaining file. The bank-statement
        # importer takes the statement's closing balance from its last row and
        # drops rows carrying no amount, so bounding the rows beforehand both
        # mis-stated that balance and yielded fewer records than the limit --
        # which in turn made `load` report end-of-file and silently import only
        # the first batch. Everything from here on is per-row, and `load`
        # applies the same bound anyway.
        window = self._batch_window(import_fields, data, options.get("limit"))
        return import_fields, data[:window]

    def _record_names(self, import_fields, merged_data, options):
        """One name per record imported in this batch, indexable by the file
        row it came from.

        :param list import_fields: field paths, **post**-merge --
            ``_handle_multi_mapping`` rebinds them to the deduplicated list, so
            an index taken from the pre-merge list addresses the wrong cell.
            With two columns mapped to the same field ahead of ``name`` -- say
            ``[city, city, name]`` -- ``index('name')`` is 1, which in the
            original row is the second ``city`` cell, and the import reported
            "FR" as the record's name.
        :param list merged_data: this batch's rows, post-merge
        :param dict options: supplies ``skip``
        :rtype: list[str]
        """
        if "name" not in import_fields:
            return []
        index_of_name = import_fields.index("name")
        # Pad the front so the client can index the result by absolute file row
        # (`resultNames[error.rows.from]`), but only when there is something to
        # align it to. `skip` is caller-supplied and the padding was dense and
        # unbounded, so `skip=5_000_000` on a four-row file allocated a
        # five-million-element list -- 44 MiB measured, linear in a number the
        # caller chooses -- to carry no names at all.
        names = [""] * (options.get("skip", 0) if merged_data else 0)
        # One name per *record*, matching `ids`: a one2many continuation row
        # belongs to the record above it and has no name of its own, so counting
        # it here shifted every later name by one against the ids the client
        # pairs them with.
        continuation = self._continuation_rows(import_fields, merged_data)
        names.extend(
            self._stringify_date_like_objects(row[index_of_name], options)
            for index, row in enumerate(merged_data)
            if not continuation[index]
        )
        return names

    def _save_column_mappings(self, columns, fields):
        """Remember the column-name -> field mapping so the next import from
        the same source can suggest it.

        :param list columns: column labels, ``False`` for unnamed columns
        :param list fields: field path per column, ``False`` where unmapped
        """
        # Only columns the user actually mapped. Storing the unmapped ones wrote
        # a `field_name = False` row for every ignored column of every import --
        # rows that can never produce a suggestion and are never vacuumed.
        #
        # Normalised through the same helper the *lookup* uses, so the two
        # cannot drift apart again: the client happens to send trimmed and
        # lower-cased labels today, and the round trip silently depended on it.
        wanted = {
            _normalize_column_name(column_name): field_name
            for column_name, field_name in zip(columns, fields, strict=False)
            if column_name and field_name
        }
        if not wanted:
            return

        BaseImportMapping = self.env["base_import.mapping"]
        # One search for all columns instead of one per column.
        existing = BaseImportMapping.search(
            [
                ("res_model", "=", self.res_model),
                ("column_name", "in", list(wanted)),
            ]
        )
        # No dedup pass over `existing`: `_column_unique_per_model` makes
        # (res_model, column_name) unique, so it cannot carry duplicates, and
        # `wanted` is a dict so the incoming side cannot either.
        for mapping in existing:
            field_name = wanted[mapping.column_name]
            if mapping.field_name != field_name:
                mapping.field_name = field_name

        missing = [
            {
                "res_model": self.res_model,
                "column_name": column_name,
                "field_name": field_name,
            }
            for column_name, field_name in wanted.items()
            if column_name not in set(existing.mapped("column_name"))
        ]
        if not missing:
            return
        # Savepoint, because this runs *after* a successful `load`: a
        # concurrent import of the same model and column can insert between
        # the search above and this create, and the resulting unique-violation
        # would abort the transaction carrying records that imported fine.
        # Remembering a mapping is a convenience; losing the import is not.
        try:
            with self.env.cr.savepoint():
                BaseImportMapping.create(missing)
        except psycopg.errors.UniqueViolation:
            _logger.debug(
                "concurrent import already stored a mapping for %s; skipping",
                self.res_model,
            )

    def _extract_binary_filenames(self, import_fields, data):
        """Pull local-filename values out of the binary columns, one entry per
        *record*, so the client can pair them with the ids ``load`` returns.

        A cell naming a local file cannot be imported as data -- the browser
        holds the bytes, not the server -- so it is blanked here and reported
        back for the client's follow-up attachment pass.

        Per record, not per row. The list used to carry one entry per data row,
        while the client zips it against ``ids``: with one2many continuation
        rows a file's row index and its record index diverge, so the pairing
        silently slid. Measured on a 3-row/2-record file, the second record was
        handed the *continuation* row's image and the third row's image was
        never uploaded at all -- an image attached to the wrong record, which
        is worse than none.

        :param list import_fields: field paths, positionally matching ``data``
        :param list data: rows of this batch, mutated in place
        :returns: ``{field_path: [filename | None, ...]}``, aligned to records
        :rtype: dict
        """
        binary_indexes = {}
        for index, path in enumerate(import_fields):
            field = self._resolve_import_path(path)
            if field is not None and field.type == "binary" and field.attachment:
                binary_indexes[path] = index
        if not binary_indexes:
            return {}

        # Blank the filename cells FIRST, then decide which rows are
        # continuations. The two are not independent: `load` sees this data
        # after the blanking, and a row whose only non-o2m value was a local
        # filename becomes a continuation precisely because that cell is now
        # empty. Deciding on the unblanked rows disagreed with `load` and put
        # the counts back out of step.
        per_row = []
        for line in data:
            row_names = {}
            for name, index in binary_indexes.items():
                value = line[index] if index < len(line) else None
                if (
                    isinstance(value, str)
                    and "." in value
                    and not re.match(config.get("import_url_regex"), value)
                ):
                    # Detect if it's a filename
                    row_names[name] = value
                    line[index] = ""
                # else base64 or a URL: nothing to do
            per_row.append(row_names)

        continuation = self._continuation_rows(import_fields, data)
        binary_filenames = {name: [] for name in binary_indexes}
        for row_index, row_names in enumerate(per_row):
            for name in binary_indexes:
                filename = row_names.get(name)
                if continuation[row_index]:
                    # This row feeds the record started above it, so its file
                    # belongs to that record -- keep it rather than drop it, but
                    # never overwrite a file that record already named.
                    if (
                        filename
                        and binary_filenames[name]
                        and not binary_filenames[name][-1]
                    ):
                        binary_filenames[name][-1] = filename
                else:
                    binary_filenames[name].append(filename)
        return binary_filenames

    def _get_merge_plan(self, mapped_field_indexes):
        """How to merge each mapped field's columns, resolved once per import.

        One entry per field: the column indexes feeding it, its type, the
        separator its type is concatenated with (``None`` when it is not
        concatenated at all) and whether char values want trimming.

        :param dict mapped_field_indexes: ``{field_path: [column index, ...]}``
        :rtype: list[tuple]
        """
        # Resolve each mapped field ONCE, ahead of the row loop. This walk
        # (`self.env[model]._fields.get(...)` per path segment) used to sit
        # inside the per-row loop even though nothing in it depends on the row:
        # a 20k-row file mapped to 3 columns performed 60k identical registry
        # resolutions. Measured 221.6 ms -> 30.1 ms.
        #
        # `_resolve_import_path` walks by *position*, which also fixes a
        # self-referential path such as 'parent_id/parent_id': the previous
        # walk compared each segment to the last one by name, so the first
        # segment matched and the model was left un-retargeted.
        merge_plan = []
        for field_path, indexes in mapped_field_indexes.items():
            field = self._resolve_import_path(field_path)
            field_type = field.type if field else ""
            merge_plan.append(
                (
                    indexes,
                    field_type,
                    CONCAT_SEPARATOR_IMPORT.get(field_type),
                    # Trim trailing whitespaces before joining
                    field_type == "char" and field.trim,
                )
            )
        return merge_plan

    def _merge_mapped_row(self, record, merge_plan, import_options):
        """One input row reduced to one value per mapped field.

        :param list record: a row of the parsed file
        :param list merge_plan: see :meth:`_get_merge_plan`
        :param dict import_options: the context's ``import_options``
        :rtype: list
        """
        new_record = []
        for indexes, field_type, separator, trim in merge_plan:
            # merge data if necessary
            if separator is not None:
                # `_stringify_date_like_objects` on every branch: the
                # xls/xlsx readers can put a native date in a char or
                # many2many column, and str.join on it raised a bare
                # TypeError that escaped execute_import as an HTTP 500.
                new_record.append(
                    separator.join(
                        self._stringify_date_like_objects(
                            record[idx], import_options, trim
                        )
                        for idx in indexes
                        if record[idx]
                    )
                )
            elif field_type == "properties":
                # for property fields date and datetime objects are not suitable for JSON values
                new_record.append(
                    self._stringify_date_like_objects(
                        record[indexes[0]], import_options
                    )
                )
            else:
                new_record.append(record[indexes[0]])
        return new_record

    def _handle_multi_mapping(self, import_fields, input_file_data):
        """This method handles multiple mapping on the same field.

        It will return the list of the mapped fields and the concatenated data for each field:

        - If two column are mapped on the same text or char field, they will end up
          in only one column, concatenated via space (char) or new line (text).
        - The same logic is used for many2many fields. Multiple values can be
          imported if they are separated by ``,``.

        Input/output Example:

        input data
            .. code-block:: python

                [
                    ["Value part 1", "1", "res.partner_id1", "Value part 2"],
                    ["I am", "1", "res.partner_id1", "Batman"],
                ]

        import_fields
            ``[desc, some_number, partner, desc]``

        output merged_data
            .. code-block:: python

                [
                    ["Value part 1 Value part 2", "1", "res.partner_id1"],
                    ["I am Batman", "1", "res.partner_id1"],
                ]
        fields
            ``[desc, some_number, partner]``
        """
        # Get fields and their occurrences indexes
        # Among the fields that have been mapped, we get their corresponding mapped column indexes
        # as multiple fields could have been mapped to multiple columns.
        mapped_field_indexes = {}
        for idx, field_path in enumerate(
            field_path for field_path in import_fields if field_path
        ):
            mapped_field_indexes.setdefault(field_path, []).append(idx)
        import_fields = list(mapped_field_indexes.keys())
        import_options = self.env.context.get("import_options", {})

        merge_plan = self._get_merge_plan(mapped_field_indexes)

        # recreate data and merge duplicates (applies to char, text, html and many2many fields)
        # Also handles multi-mapping on "field of relation fields".
        merged_data = [
            self._merge_mapped_row(record, merge_plan, import_options)
            for record in input_file_data
        ]

        return import_fields, merged_data

    def _update_fallback_accepted_values(self, fallback_values):
        """Record, per fallback field, the set of values it actually accepts.

        Adds an ``accepted_values`` key in place. Boolean and selection fields
        get one; any other type gets none, which the caller reads as "leave the
        cell alone".

        :param dict fallback_values: see :meth:`_handle_fallback_values`
        """
        # What counts as "a value this field accepts" is `ir.fields.converter`'s
        # answer, not a second list kept here. This used to build
        #
        #     selection_values = [str(value).lower() for _key, value in selection]
        #
        # where `value` is the LABEL -- so a cell carrying the field's own
        # stored value was "invalid" and got replaced by the fallback, silently,
        # even though the converter downstream accepts it. 30 stored writable
        # selection fields in a `base` + `base_import` registry have at least
        # one value the labels do not cover, and `ir.sequence.implementation`
        # imported `no_gap` as `standard` the moment a fallback was configured
        # for the column. Asking the converter also picks up the labels of every
        # installed language, which it accepts and this never did.
        converter = self.env["ir.fields.converter"]
        for field_string, fallback in fallback_values.items():
            target_field = field_string.split("/")[-1]
            target_model = self.env[fallback["field_model"]]
            field = target_model._fields.get(target_field)

            if fallback["field_type"] == "boolean":
                trues, falses = converter._get_boolean_tokens()
                fallback["accepted_values"] = trues | falses
                continue
            if fallback["field_type"] != "selection":
                continue

            if field is not None and field.type == "selection":
                fallback["accepted_values"] = frozenset(
                    converter._get_selection_index(field)
                )
                continue
            # A Properties sub-column ("<field>.<property>") is not a field of
            # the model, so there is nothing to ask the converter about. The
            # client already sends the selection for those (it reads it off the
            # field tree), so honour that.
            selection = fallback.get("selection") or []
            fallback["accepted_values"] = frozenset(
                str(token).lower() for pair in selection for token in pair
            )

    def _apply_fallback_value(self, value, fallback):
        """One cell, replaced by its fallback when the field would refuse it.

        :param value: the raw cell
        :param dict fallback: one entry of ``fallback_values``, already through
            :meth:`_update_fallback_accepted_values`
        """
        # A spreadsheet date cell reaching here is not a str, and
        # `.lower()` on it raised a bare AttributeError that escaped
        # execute_import as an HTTP 500.
        value = self._stringify_date_like_objects(
            value, self.env.context.get("import_options", {})
        )
        # Only boolean and selection get an accept-list; for any
        # other type the cell stands, as it always has. Indexing
        # unconditionally here would turn a client sending a third
        # field_type into a KeyError, and so into an HTTP 500.
        accepted = fallback.get("accepted_values")
        if accepted is not None and value.lower() not in accepted:
            # "skip" means leave the cell empty rather than guess
            fallback_value = fallback["fallback_value"]
            return fallback_value if fallback_value != "skip" else None
        return value

    def _handle_fallback_values(self, import_field, input_file_data, fallback_values):
        """
        If there are fallback values, this method will replace the input file
        data value if it does not match the possible values for the given field.
        This is only valid for boolean and selection fields.

        .. note::

            We can consider that we need to retrieve the selection values for
            all the fields in fallback_values, as if they are present, it's because
            there was already a conflict during first import run and user had to
            select a fallback value for the field.

        :param list import_field: ordered list of field that have been matched to import data
        :param list input_file_data: ordered list of values (list) that need to be imported in
            the given import_fields
        :param dict fallback_values:

            contains all the fields that have been tagged by the user to use a
            specific fallback value in case the value to import does not match
            values accepted by the field (selection or boolean) e.g.::

                {
                    "fieldName": {
                        "fallback_value": fallback_value,
                        "field_model": field_model,
                        "field_type": field_type,
                    },
                    "state": {
                        "fallback_value": "draft",
                        "field_model": field_model,
                        "field_type": "selection",
                    },
                    "active": {
                        "fallback_value": "true",
                        "field_model": field_model,
                        "field_type": "boolean",
                    },
                }
        """
        self._update_fallback_accepted_values(fallback_values)

        # check fallback values
        for record_index, records in enumerate(input_file_data):
            for column_index, value in enumerate(records):
                field = import_field[column_index]
                if field in fallback_values:
                    input_file_data[record_index][column_index] = (
                        self._apply_fallback_value(value, fallback_values[field])
                    )

        return input_file_data


_SEPARATORS = [" ", "/", "-", ".", ""]
_PATTERN_BASELINE = [
    ("%m", "%d", "%Y"),
    ("%d", "%m", "%Y"),
    ("%Y", "%m", "%d"),
    ("%Y", "%d", "%m"),
]
DATE_FORMATS = []
# take the baseline format and duplicate it substituting the long
# year (%Y) with the short year (%y)
for ps in _PATTERN_BASELINE:
    patterns = {ps}
    for s, t in [("%Y", "%y")]:
        patterns.update(
            [  # need listcomp: with genexpr "set changed size during iteration"
                tuple(t if it == s else it for it in f) for f in patterns
            ]
        )
    DATE_FORMATS.extend(patterns)
DATE_PATTERNS = [sep.join(fmt) for sep in _SEPARATORS for fmt in DATE_FORMATS]
TIME_PATTERNS = [
    "%H:%M:%S",
    "%H:%M",
    "%H",  # 24h
    "%I:%M:%S %p",
    "%I:%M %p",
    "%I %p",  # 12h
]

_INTEGER_RE = re.compile(r"^[+-]?[0-9]+$")


def _normalize_column_name(name):
    """The key a column name is stored and looked up under in
    ``base_import.mapping``.

    Both sides must agree, and they used to only by accident: the client saved
    ``name.trim().toLowerCase()`` while the server looked up ``header.lower()``.
    A header carrying the surrounding whitespace that spreadsheet exports
    routinely produce -- ``" Kunde Nr "`` -- therefore never matched the
    mapping the user had already taught the system. Normalising here makes the
    client's trimming a convenience rather than load-bearing.

    :param str name: raw column label from the file or the client
    :rtype: str
    """
    return (name or "").strip().lower()


def _is_native_date_column(values):
    """Whether the reader has already resolved this column to date objects.

    The xls/xlsx readers hand back native ``datetime.date`` /
    ``datetime.datetime`` for date-formatted cells, and such a column must not
    be put through :func:`get_matching_pattern`: that function *skips* date
    instances, so every candidate pattern matches vacuously over the column and
    the FIRST one is returned as though it had been confirmed. The answer is
    then written into ``options["date_format"]`` -- measured, a sheet of native
    dates pinned it to the user's language format on no evidence at all -- and
    the client renders it as the format the file is in. Answering directly
    yields the same types the vacuous match produced, so no mapping suggestion
    changes; only the false claim about the file's format goes away.

    Empty cells are ignored, but an all-empty column is not a date column.
    :meth:`_extract_header_types` answers that case (``["all"]``) before
    reaching here; this returns False for it anyway so the predicate stands on
    its own.

    :param list values: one column's preview values
    :rtype: bool
    """
    populated = [value for value in values if value]
    return bool(populated) and all(
        isinstance(value, datetime.date) for value in populated
    )


def _is_integer_literal(value):
    """Whether ``value`` is an ASCII integer literal, optionally signed.

    Not ``str.isdigit``: that rejects "-1" and accepts non-ASCII digits such as
    "٣" and "²", which ``int()`` then refuses.
    """
    return bool(_INTEGER_RE.match(value))


def get_matching_pattern(patterns, values):
    for pattern in patterns:
        p = to_re(pattern)
        for val in values:
            if isinstance(val, datetime.date):
                continue
            if val and not p.match(val):
                break

        else:  # no break, all match
            return pattern

    return None


@functools.lru_cache(maxsize=1024)
def to_re(pattern):
    """cut down version of TimeRE converting strptime patterns to regex

    Memoized: `get_matching_pattern` walks ~280 candidate date/datetime patterns per
    column per preview, and the pattern set is a module-level constant.
    """
    pattern = re.sub(r"\s+", r"\\s+", pattern)
    pattern = re.sub(r"%([a-z])", _replacer, pattern, flags=re.IGNORECASE)
    pattern = "^" + pattern + "$"
    return re.compile(pattern, re.IGNORECASE)


def _replacer(m):
    return _P_TO_RE[m.group(1)]


_P_TO_RE = {
    "d": r"(3[0-1]|[1-2]\d|0[1-9]|[1-9]| [1-9])",
    "H": r"(2[0-3]|[0-1]\d|\d)",
    "I": r"(1[0-2]|0[1-9]|[1-9])",
    "m": r"(1[0-2]|0[1-9]|[1-9])",
    "M": r"([0-5]\d|\d)",
    "S": r"(6[0-1]|[0-5]\d|\d)",
    "y": r"(\d\d)",
    "Y": r"(\d\d\d\d)",
    "p": r"(am|pm)",
    "%": "%",
}


def _prepare_read_file_error(exc: Exception, message: str) -> UserError:
    # exc_info=exc (not True): this function can be called after the original
    # except frame that produced `exc` is no longer the active exception, in
    # which case exc_info=True would silently log no traceback at all (t24068).
    #
    # Logged at debug, not warning: an unreadable upload is a user error, not a
    # server fault, and the message below already reaches the user. Emitting a
    # full traceback per failed candidate format also made log volume quadratic
    # whenever the readers nested (each frame re-renders the whole __context__
    # chain) -- one crafted upload produced ~240 MiB of log text and ~60s of
    # formatting. The dispatch allow-list now prevents the nesting; keeping this
    # at debug removes the amplification itself.
    _logger.debug(message, exc_info=exc)
    e = UserError(message)
    e.__cause__ = exc
    return e


register_reader(
    _SpreadsheetReader("xlsx", mimetypes_for("xlsx"), read_xlsx_rows, "openpyxl")
)
register_reader(_SpreadsheetReader("xls", mimetypes_for("xls"), read_xls_rows, "xlrd"))
register_reader(_SpreadsheetReader("ods", mimetypes_for("ods"), read_ods_rows, "odf"))
