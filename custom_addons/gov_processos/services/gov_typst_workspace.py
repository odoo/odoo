import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class GovTypstWorkspace:
    """
    Materializa dados.typ + template.typ em um workspace temporario.
    """

    def __init__(self, env=None):
        self.env = env
        self.render_log = ""
        self.last_hash = False

    def compile(self, dados_typ_text, template_typ_text):
        with tempfile.TemporaryDirectory(prefix="gov_typst_") as tmpdir:
            tmp_path = Path(tmpdir)
            self._materialize(tmp_path, dados_typ_text, template_typ_text)
            output_path = tmp_path / "output.pdf"
            self.render_log = self._run_compile(tmp_path / "template.typ", output_path)
            pdf_bytes = output_path.read_bytes()
            self.last_hash = hashlib.sha256(pdf_bytes).hexdigest()
            return pdf_bytes

    def _materialize(self, workdir, dados_typ_text, template_typ_text):
        (workdir / "dados.typ").write_text(dados_typ_text or "", encoding="utf-8")
        (workdir / "template.typ").write_text(template_typ_text or "", encoding="utf-8")

        assets_dir = os.environ.get("TYPST_ASSETS_DIR")
        if assets_dir and Path(assets_dir).is_dir():
            shutil.copytree(assets_dir, workdir / "assets")

        payload = {
            "generator": "gov.processo.doc.render.job",
            "dados_sha256": hashlib.sha256((dados_typ_text or "").encode("utf-8")).hexdigest(),
            "template_sha256": hashlib.sha256(
                (template_typ_text or "").encode("utf-8")
            ).hexdigest(),
        }
        (workdir / "payload.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _run_compile(template_path, output_path):
        typst_bin = os.environ.get("TYPST_BIN") or shutil.which("typst")
        timeout = int(os.environ.get("TYPST_TIMEOUT", 30))
        if not typst_bin:
            raise RuntimeError(
                "Binario 'typst' nao encontrado. Configure TYPST_BIN ou instale o Typst."
            )

        try:
            result = subprocess.run(
                [typst_bin, "compile", str(template_path), str(output_path)],
                cwd=str(template_path.parent),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Compilacao Typst excedeu {timeout} segundos.") from exc

        log = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0 or not output_path.exists():
            raise RuntimeError(
                "Falha ao compilar Typst. "
                + ((result.stderr or result.stdout or "").strip()[:1000] or "Verifique o template.")
            )
        return log
