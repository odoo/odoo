# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import glob
import io
import os
import tarfile
import tempfile

from odoo import fields, models, release, _
from odoo.modules.module import get_module_path, get_modules
from odoo.tools import file_open


class LanguagePack(models.Model):
    _name = "i18n.pack"
    _description = "Language Packs"
    content = fields.Binary(
        string="Translation Archive",
        help="Compressed archived containing the translations",
        required=True,
    )
    lang_code = fields.Char(
        string="Language Code",
        help="ISO code of the language included in the pack. "
        "One pack can include more than one language (e.g. 'fr' includes 'fr.po' and fr_BE.po').",
        required=True,
    )
    version = fields.Char(
        help="Version of the Odoo server using the pack (e.g. '13.0', 'saas~14.3', '15.0alpha1')",
        required=True,
    )
    description = fields.Text(help="Description of the archive (e.g. the module it contains)")
    fname = fields.Char(string="Archive Filename", compute="_compute_display_name")

    _sql_constraint = [
        (
            "unique_lang_version",
            "UNIQUE(lang_code, version)",
            "Only one language pack is possible per version",
        )
    ]

    def _compute_display_name(self):
        for pack in self:
            pack.display_name = pack.version + " - " + pack.lang_code
            pack.fname = pack.version + " - " + pack.lang_code + ".tar.xz"

    def _generate_pack(self, languages, modules=None):
        """ Generate i18n.packs

        Based on the local po files inside the i18n/ directories
        :param languages: a recordset of model res.lang, a pack will be generated using
            the base language code (e.g. fr_FR and fr_BE will be in the same pack 'fr')
        :param modules: a list of module name. If set, a pack will contain the
            translation files for these modules only. If not set, all modules inside
            the addons-path will be used.
        """
        langs = {lang.split("_")[0].split("@")[0] for lang in languages.mapped("code")}
        version = release.version.split('+')[0]  # remove +e part if present

        addons_path = {}
        if not modules:
            modules = get_modules()
        for module in modules:
            addons_path[module] = get_module_path(module)

        for code in langs:
            with tempfile.TemporaryFile(mode="w+b") as fileobj:
                with tarfile.open(mode="x:xz", fileobj=fileobj) as tar:

                    for module, path in addons_path.items():
                        if not path:
                            # invalid module
                            continue

                        i18n_path = os.path.join(path, "i18n", code + "*.po")
                        for filename in glob.glob(i18n_path):
                            # convert path to format '<module>/i18n/<lang>.po'
                            # for file_open and use it as filename inside the archive
                            local_path = "/".join(filename.split("/")[-3:])
                            info = tarfile.TarInfo(local_path)
                            with file_open(local_path, mode="rb") as file:
                                # compute filesize
                                file.seek(0, io.SEEK_END)
                                info.size = file.tell()
                                file.seek(0, io.SEEK_SET)

                                tar.addfile(info, file)

                fileobj.seek(0)
                archive = base64.b64encode(fileobj.read()).decode()

            existing_pack = self.search(
                [("lang_code", "=", code), ("version", "=", version)]
            )
            if existing_pack:
                existing_pack.write({"content": archive, "description": ", ".join(modules)})
            else:
                self.create({
                    "content": archive,
                    "lang_code": code,
                    "version": version,
                    "description": _("Language pack for modules: %s") % ", ".join(modules),
                })

    def _generate_all_packs(self):
        """ Generate language packs for all active languages """
        langs = self.env["res.lang"].search([])
        self._generate_pack(languages=langs)
