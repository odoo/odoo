import os
import subprocess
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.gov_processos.models.gov_typst_service import GovTypstService


class TestGovTypstService(TransactionCase):
    def test_compile_writes_extra_images_before_running_typst(self):
        def fake_run(args, cwd, capture_output, text, timeout, check):
            with open(os.path.join(cwd, "timbre_cabecalho.png"), "rb") as handle:
                self.assertEqual(handle.read(), b"header-bytes")
            with open(os.path.join(cwd, "timbre_rodape.png"), "rb") as handle:
                self.assertEqual(handle.read(), b"footer-bytes")
            with open(os.path.join(cwd, "main.pdf"), "wb") as handle:
                handle.write(b"%PDF-1.4 test")
            return subprocess.CompletedProcess(args, 0, "", "")

        with patch(
            "odoo.addons.gov_processos.models.gov_typst_service.shutil.which",
            return_value="/usr/bin/typst",
        ), patch(
            "odoo.addons.gov_processos.models.gov_typst_service.subprocess.run",
            side_effect=fake_run,
        ):
            pdf_bytes = GovTypstService.compile(
                '= "Documento com timbre"',
                extra_images={
                    "cabecalho": b"header-bytes",
                    "rodape": b"footer-bytes",
                },
                timeout=10,
            )

        self.assertEqual(pdf_bytes, b"%PDF-1.4 test")
