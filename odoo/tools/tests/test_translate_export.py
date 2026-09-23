import io
import tarfile
import unittest
from unittest.mock import patch

from odoo.tools.translate import (
    PoFileWriter,
    TarFileWriter,
    TranslationModuleReader,
)

_MODULES = [f"module_{name}" for name in "qwertyuiopasdfghjklz"]


def _row(module, src="Term"):
    return (module, "code", "addons/x.py", 0, src, "", ())


class TestPoFileWriterHeader(unittest.TestCase):
    def test_header_lists_modules_in_sorted_order(self):
        buffer = io.BytesIO()
        PoFileWriter(buffer, lang=None).write_rows([_row(m) for m in _MODULES])
        listed = [
            line.removeprefix("# \t* ")
            for line in buffer.getvalue().decode().splitlines()
            if line.startswith("# \t* ")
        ]
        self.assertEqual(listed, sorted(_MODULES))


class TestTarFileWriter(unittest.TestCase):
    def test_archive_holds_one_file_per_module(self):
        buffer = io.BytesIO()
        TarFileWriter(buffer, lang="fr_FR").write_rows([_row("mod_a"), _row("mod_b")])
        buffer.seek(0)
        with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
            self.assertEqual(
                sorted(tar.getnames()), ["mod_a/i18n/fr_FR.po", "mod_b/i18n/fr_FR.po"]
            )

    def test_archive_is_closed_when_a_row_fails(self):
        opened = []
        real_open = tarfile.open

        def recording_open(*args, **kwargs):
            opened.append(real_open(*args, **kwargs))
            return opened[-1]

        with patch.object(tarfile, "open", recording_open):
            writer = TarFileWriter(io.BytesIO(), lang="fr_FR")
            with self.assertRaises(ValueError):
                writer.write_rows([("mod_a", "malformed")])
        self.assertTrue(all(tar.closed for tar in opened))


class _FakeModules:
    def __init__(self):
        self.asked = []

    def _extract_resource_attachment_translations(self, module, lang):
        self.asked.append(module)
        if module == "imported_mod":
            yield (module, "code", "addons/imported_mod/a.js", 1, "Imported term")


class TestModuleReaderAttachmentTerms(unittest.TestCase):
    def _reader(self, modules):
        fake = _FakeModules()
        reader = TranslationModuleReader.__new__(TranslationModuleReader)
        reader._cr = None
        reader._lang = "fr_FR"
        reader.env = {"ir.module.module": fake}
        reader._to_translate = []
        reader._modules = modules
        reader._installed_modules = ["web", "imported_mod"]
        reader._path_list = []
        return reader, fake

    def test_all_asks_every_installed_module(self):
        reader, fake = self._reader(["all"])
        reader._export_translatable_resources()
        self.assertEqual(fake.asked, ["web", "imported_mod"])
        self.assertIn("Imported term", [row[4] for row in reader])

    def test_named_modules_are_asked_as_given(self):
        reader, fake = self._reader(["imported_mod"])
        reader._export_translatable_resources()
        self.assertEqual(fake.asked, ["imported_mod"])


if __name__ == "__main__":
    unittest.main()
