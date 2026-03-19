import os
import shutil
import subprocess
import tempfile
import uuid

from odoo.exceptions import UserError


class GovTypstService:
    """Compilador simples de Typst para PDF."""

    @classmethod
    def compile(cls, typst_source, timeout=30):
        typst_path = shutil.which("typst")
        if not typst_path:
            raise UserError(
                "O binario 'typst' nao foi encontrado no servidor. "
                "Instale o Typst para compilar documentos nesse formato."
            )

        source = (typst_source or "").strip()
        if not source:
            raise UserError("Nenhum conteudo Typst encontrado para compilar.")

        tmp_dir = tempfile.mkdtemp(prefix=f"gov_typst_{uuid.uuid4().hex[:8]}_")
        source_path = os.path.join(tmp_dir, "main.typ")
        pdf_path = os.path.join(tmp_dir, "main.pdf")
        try:
            with open(source_path, "w", encoding="utf-8") as handle:
                handle.write(source)

            result = subprocess.run(
                [typst_path, "compile", source_path, pdf_path],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            if result.returncode != 0 or not os.path.exists(pdf_path):
                stderr = (result.stderr or result.stdout or "").strip()
                raise UserError(
                    "Falha ao compilar Typst. "
                    + (stderr[:800] or "Verifique a sintaxe do documento.")
                )

            with open(pdf_path, "rb") as handle:
                return handle.read()
        except subprocess.TimeoutExpired as exc:
            raise UserError("Tempo limite excedido na compilacao Typst.") from exc
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
