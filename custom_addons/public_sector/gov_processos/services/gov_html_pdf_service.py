"""
GovHtmlPdfService - Converte HTML em PDF via wkhtmltopdf.

Extraído de gov_latex_service.py para separação de responsabilidades.
"""
import os
import shutil
import subprocess
import tempfile
import uuid
from html import escape as html_escape

from odoo.exceptions import UserError


class GovHtmlPdfService:
    """Converte HTML em PDF via wkhtmltopdf."""

    @classmethod
    def is_available(cls):
        return shutil.which("wkhtmltopdf") is not None

    @classmethod
    def compile(cls, html_content, header_html=None, footer_html=None, timeout=30):
        """Converte HTML em PDF via wkhtmltopdf e retorna bytes."""
        wk_path = shutil.which("wkhtmltopdf")
        if not wk_path:
            raise UserError(
                "wkhtmltopdf nao encontrado. Instale o binario ou "
                "use a aba Fonte LaTeX para gerar o PDF."
            )

        tmp_dir = tempfile.mkdtemp(prefix=f"gov_html_{uuid.uuid4().hex[:8]}_")
        try:
            html_path = os.path.join(tmp_dir, "main.html")
            pdf_path = os.path.join(tmp_dir, "main.pdf")
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(html_content or "")

            cmd = [
                wk_path,
                "--encoding", "utf-8",
                "--margin-top", "25mm",
                "--margin-bottom", "25mm",
                "--margin-left", "30mm",
                "--margin-right", "20mm",
                "--page-size", "A4",
                "--quiet",
            ]

            if header_html:
                header_path = os.path.join(tmp_dir, "header.html")
                with open(header_path, "w", encoding="utf-8") as fh:
                    fh.write(header_html)
                cmd += ["--header-html", header_path, "--header-spacing", "5"]

            if footer_html:
                footer_path = os.path.join(tmp_dir, "footer.html")
                with open(footer_path, "w", encoding="utf-8") as fh:
                    fh.write(footer_html)
                cmd += ["--footer-html", footer_path, "--footer-spacing", "5"]

            cmd += [html_path, pdf_path]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                cwd=tmp_dir,
                check=False,
            )
            if result.returncode != 0 or not os.path.exists(pdf_path):
                stderr = result.stderr.decode("utf-8", errors="replace")
                raise UserError(f"Erro no wkhtmltopdf:\n{stderr[:500]}")

            with open(pdf_path, "rb") as fh:
                return fh.read()
        except subprocess.TimeoutExpired as exc:
            raise UserError(f"wkhtmltopdf excedeu {timeout} segundos.") from exc
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    @classmethod
    def build_html_with_timbre(cls, content_html, timbre):
        """
        Monta HTML completo + header/footer para wkhtmltopdf.
        Retorna (html_body, header_html, footer_html).
        """
        cor1 = (
            getattr(timbre, "rodape_cor_barra_superior", None) if timbre else None
        ) or "1F4E79"
        cor2 = (
            getattr(timbre, "rodape_cor_barra_inferior", None) if timbre else None
        ) or "2E75B6"
        orgao = html_escape(
            (getattr(timbre, "orgao_nome", None) if timbre else None) or "Orgao Publico"
        )
        secretaria = html_escape(
            (getattr(timbre, "secretaria_nome", None) if timbre else None) or ""
        )

        cabecalho_tag = ""
        if timbre and getattr(timbre, "cabecalho_img", False):
            cabecalho_tag = (
                '<img src="data:image/png;base64,'
                + timbre.cabecalho_img
                + '" style="width:100%; max-height:120px;'
                ' object-fit:contain; margin-bottom:6px;"/>'
            )

        rodape_tag = ""
        if timbre and getattr(timbre, "rodape_img", False):
            rodape_tag = (
                '<img src="data:image/png;base64,'
                + timbre.rodape_img
                + '" style="width:100%; max-height:70px; object-fit:contain;"/>'
            )

        header_html = f"""
<html><body style="margin:0; padding:4px 20px;">
  <div style="border-top:6px solid #{cor1}; padding-top:4px;">
    {cabecalho_tag}
    <strong style="font-size:13px;">{orgao}</strong><br/>
    <span style="font-size:11px; color:#555;">{secretaria}</span>
  </div>
</body></html>
"""
        footer_html = f"""
<html><body style="margin:0; padding:2px 20px;
  border-top:2px solid #{cor2}; font-size:10px; color:#555;">
  {rodape_tag}
  <span>Gerado pelo Sistema AGI Gov</span>
  <span style="float:right;">
    Pagina <span class="page"></span> de <span class="topage"></span>
  </span>
</body></html>
"""
        html_body = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <style>
    body {{ font-family: Arial, sans-serif; font-size: 12pt;
           line-height: 1.6; color: #222; }}
    h1, h2, h3 {{ color: #{cor1}; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 6px; }}
  </style>
</head>
<body>{content_html or ''}</body>
</html>"""
        return html_body, header_html, footer_html
