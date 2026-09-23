import zipfile

from odoo.exceptions import UserError
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)

# `.ods`/`.xlsx` are both zip archives, and their parsing libraries (odfpy,
# openpyxl) read some members fully into memory -- `content.xml`, embedded
# pictures, thumbnails for odfpy; the shared-strings table for openpyxl, even
# in `read_only` mode -- via plain `zipfile`-backed reads, with no size guard
# of their own. A member's declared uncompressed size is fully controlled by
# the file's author, so a small upload can decompress to gigabytes before
# the ODS reader's own MAX_CELL_REPEAT/MAX_ROW_REPEAT (or, for `.xlsx`, any
# row-emptiness filter) ever see a single cell (a zip bomb). Checked
# ahead of handing the file to either library, against the archive's own
# declared sizes -- cheap, since it only reads the central directory, never
# a member's data. It lives here, and not beside the ODS reader it started
# in, because that module imports odfpy: the `.xlsx` path would then need an
# optional `.ods` library installed to read a spreadsheet it never opens.
MAX_UNCOMPRESSED_MEMBER_SIZE = 100 * 1024 * 1024  # 100 MiB


def check_zip_member_sizes(file):
    """Raise if any member of the zip archive would decompress past
    :data:`MAX_UNCOMPRESSED_MEMBER_SIZE`, before handing it to a parsing
    library (odfpy for `.ods`, openpyxl for `.xlsx`).

    :param file: a file-like object holding the zip archive
    :raises UserError: on the first oversized member

    A `UserError` and not a `ValueError`, because both callers are import
    readers and `BaseImport._get_preview_error` renders this message into the
    import UI verbatim -- measured: `parse_preview` on an archive over the cap
    answers `{"error": "Import file … would expand to more than … MiB, …"}`.
    It is a sentence the person who uploaded the file reads, so it is
    translated; a builtin exception carrying gettext is a developer diagnostic
    booked into the catalogue, which is what `gettext-developer-error` exists
    to stop and what this is not.
    """
    with zipfile.ZipFile(file) as archive:
        for info in archive.infolist():
            if info.file_size > MAX_UNCOMPRESSED_MEMBER_SIZE:
                raise UserError(
                    _lt(
                        "Import file %(member)s would expand to more than "
                        "%(cap)s MiB, which is not supported.",
                        member=info.filename,
                        cap=MAX_UNCOMPRESSED_MEMBER_SIZE // (1024 * 1024),
                    )
                )
