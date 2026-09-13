import base64
import logging
import operator
from pathlib import Path
from tempfile import TemporaryFile

from odoo import fields, models, tools
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools.translate import TranslationImporter

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class BaseLanguageImport(models.TransientModel):
    _name = "base.language.import"
    _description = "Language Import"

    name = fields.Char(
        string="Language Name",
        required=True,
    )
    code = fields.Char(
        string="ISO Code",
        required=True,
        help="ISO Language and Country code, e.g. en_US",
    )
    data = fields.Binary(
        string="File",
        attachment=False,
        required=True,
    )
    filename = fields.Char(
        string="File Name",
        required=True,
    )
    overwrite = fields.Boolean(
        string="Overwrite Existing Terms",
        default=True,
        help="If you enable this option, existing translations (including custom ones) "
        "will be overwritten and replaced by those in this file",
    )

    def import_lang(self) -> bool:
        Lang = self.env["res.lang"]
        for overwrite, base_lang_imports in tools.groupby(
            self, operator.itemgetter("overwrite")
        ):
            translation_importer = TranslationImporter(self.env.cr)
            for base_lang_import in base_lang_imports:
                if not Lang._activate_lang(base_lang_import.code):
                    Lang._create_lang(
                        base_lang_import.code, lang_name=base_lang_import.name
                    )
                try:
                    with TemporaryFile("wb+") as buf:
                        buf.write(base64.decodebytes(base_lang_import.data))
                        fileformat = Path(base_lang_import.filename).suffix[1:].lower()
                        translation_importer.load(
                            buf, fileformat, base_lang_import.code
                        )
                except Exception as e:
                    _logger.warning(
                        "Could not import the file due to a format mismatch or it being malformed."
                    )
                    raise UserError(
                        self.env._(
                            'File "%(file_name)s" not imported due to format mismatch or a malformed file.'
                            " (Valid formats are .csv, .po)\n\nTechnical Details:\n%(error_message)s",
                            file_name=base_lang_import.filename,
                            error_message=e,
                        ),
                    ) from e
            _debug.pipeline(
                "import_language",
                langs=[imp.code for imp in base_lang_imports],
                overwrite=overwrite,
            )
            translation_importer.save(overwrite=overwrite)
        return True
