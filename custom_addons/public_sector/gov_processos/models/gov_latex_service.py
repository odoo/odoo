import base64
import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from html import escape as html_escape

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from pylatexenc.latexwalker import LatexWalker, LatexWalkerError

    _PYLATEXENC_AVAILABLE = True
except ImportError:
    _PYLATEXENC_AVAILABLE = False
    _logger.warning(
        "pylatexenc nao instalado. Validacao previa de LaTeX desabilitada."
    )


class GovLatexService:
    """
    Servico de compilacao LaTeX -> PDF.
    Uso: GovLatexService.compile(latex_source) -> bytes (PDF)
    """

    _PREAMBULO_PADRAO = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[brazil]{babel}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{fancyhdr}
\usepackage{xcolor}
\geometry{top=2.5cm,bottom=2.5cm,left=3cm,right=2cm}
"""

    @classmethod
    def _prepare_source(cls, latex_source):
        source = (latex_source or "").strip()
        if not source:
            return source
        if r"\documentclass" in source:
            return source
        return (
            cls._PREAMBULO_PADRAO
            + "\n\\begin{document}\n"
            + source
            + "\n\\end{document}\n"
        )

    @classmethod
    def validate_latex(cls, latex_source):
        """
        Valida sintaticamente o LaTeX com pylatexenc.
        Retorna uma lista de avisos.
        """
        if not _PYLATEXENC_AVAILABLE:
            return []
        warnings = []
        try:
            walker = LatexWalker(latex_source or "")
            walker.get_latex_nodes()
        except LatexWalkerError as exc:
            warnings.append(str(exc))
        except Exception as exc:  # pragma: no cover - defesa
            warnings.append(f"Erro inesperado na validacao: {exc}")
        return warnings

    @classmethod
    def _save_image_blob(cls, tmp_dir, name, data):
        if not data:
            return
        ext = "jpg" if data[:3] == b"\xff\xd8\xff" else "png"
        path_with_ext = os.path.join(tmp_dir, f"{name}.{ext}")
        with open(path_with_ext, "wb") as file_with_ext:
            file_with_ext.write(data)

        path_no_ext = os.path.join(tmp_dir, name)
        with open(path_no_ext, "wb") as file_no_ext:
            file_no_ext.write(data)

    @classmethod
    def compile(cls, latex_source, logo_binary=None, extra_images=None, timeout=30):
        """
        Compila LaTeX em PDF e retorna bytes.
        """
        pdflatex_path = shutil.which("pdflatex")
        if not pdflatex_path:
            raise UserError(
                "pdflatex nao encontrado no servidor. "
                "Instale TeX Live/MiKTeX para habilitar a compilacao."
            )

        final_source = cls._prepare_source(latex_source)
        warnings = cls.validate_latex(final_source)
        if warnings:
            _logger.warning("Avisos de validacao LaTeX: %s", warnings)

        tmp_dir = tempfile.mkdtemp(prefix=f"gov_latex_{uuid.uuid4().hex[:8]}_")
        try:
            tex_path = os.path.join(tmp_dir, "main.tex")
            with open(tex_path, "w", encoding="utf-8") as tex_file:
                tex_file.write(final_source)

            if logo_binary:
                cls._save_image_blob(tmp_dir, "logo", logo_binary)

            if extra_images:
                for nome, dados in (extra_images or {}).items():
                    if dados:
                        cls._save_image_blob(tmp_dir, nome, dados)

            for passagem in range(2):
                result = subprocess.run(
                    [
                        pdflatex_path,
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        "-no-shell-escape",
                        "-output-directory=.",
                        "main.tex",
                    ],
                    capture_output=True,
                    timeout=timeout,
                    cwd=tmp_dir,
                    check=False,
                )
                if result.returncode != 0:
                    stdout = result.stdout.decode("utf-8", errors="replace")
                    stderr = result.stderr.decode("utf-8", errors="replace")
                    log_path = os.path.join(tmp_dir, "main.log")
                    log_tail = ""
                    if os.path.exists(log_path):
                        with open(log_path, "r", encoding="utf-8", errors="replace") as log_file:
                            log_tail = "\n".join(log_file.read().splitlines()[-40:])
                    erros = [line for line in stdout.splitlines() if line.startswith("!")]
                    msg_erro = "\n".join(erros[:10]) or log_tail or stderr or stdout[-600:]
                    raise UserError(
                        f"Erro na compilacao LaTeX (passagem {passagem + 1}):\n\n{msg_erro}"
                    )

            pdf_path = os.path.join(tmp_dir, "main.pdf")
            if not os.path.exists(pdf_path):
                raise UserError("PDF nao foi gerado. Verifique o codigo LaTeX.")
            with open(pdf_path, "rb") as pdf_file:
                return pdf_file.read()
        except subprocess.TimeoutExpired as exc:
            raise UserError(
                f"Compilacao LaTeX excedeu {timeout} segundos. "
                "Verifique se o documento nao possui processamento excessivo."
            ) from exc
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    @classmethod
    def compile_with_timbre(
        cls,
        latex_source,
        timbre=None,
        fallback_logo_binary=None,
        timeout=30,
    ):
        logo_binary = fallback_logo_binary
        extra_images = {}

        if timbre:
            if hasattr(timbre, "get_imagens_para_latex"):
                try:
                    extra_images = timbre.get_imagens_para_latex() or {}
                except Exception as exc:
                    _logger.warning("Falha ao obter imagens do timbre %s: %s", timbre.id, exc)
                    extra_images = {}

            if not logo_binary:
                try:
                    cabecalho = extra_images.get("cabecalho")
                    if cabecalho:
                        logo_binary = cabecalho
                except Exception:
                    logo_binary = None

        return cls.compile(
            latex_source,
            logo_binary=logo_binary,
            extra_images=extra_images,
            timeout=timeout,
        )

    @classmethod
    def compile_to_base64(
        cls,
        latex_source,
        logo_binary=None,
        extra_images=None,
        timeout=30,
    ):
        """
        Compila e retorna (base64_pdf, sha256_hash).
        """
        pdf_bytes = cls.compile(
            latex_source,
            logo_binary=logo_binary,
            extra_images=extra_images,
            timeout=timeout,
        )
        b64_pdf = base64.b64encode(pdf_bytes).decode("ascii")
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        return b64_pdf, sha256


class GovHtmlPdfService:
    """
    Fallback: converte HTML em PDF via wkhtmltopdf.
    """

    @classmethod
    def is_available(cls):
        return shutil.which("wkhtmltopdf") is not None

    @classmethod
    def compile(cls, html_content, header_html=None, footer_html=None, timeout=30):
        """
        Converte HTML em PDF via wkhtmltopdf e retorna bytes.
        """
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
            with open(html_path, "w", encoding="utf-8") as html_file:
                html_file.write(html_content or "")

            cmd = [
                wk_path,
                "--encoding",
                "utf-8",
                "--margin-top",
                "25mm",
                "--margin-bottom",
                "25mm",
                "--margin-left",
                "30mm",
                "--margin-right",
                "20mm",
                "--page-size",
                "A4",
                "--quiet",
            ]

            if header_html:
                header_path = os.path.join(tmp_dir, "header.html")
                with open(header_path, "w", encoding="utf-8") as header_file:
                    header_file.write(header_html)
                cmd += ["--header-html", header_path, "--header-spacing", "5"]

            if footer_html:
                footer_path = os.path.join(tmp_dir, "footer.html")
                with open(footer_path, "w", encoding="utf-8") as footer_file:
                    footer_file.write(footer_html)
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

            with open(pdf_path, "rb") as pdf_file:
                return pdf_file.read()
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
        cor1 = (getattr(timbre, "rodape_cor_barra_superior", None) if timbre else None) or "1F4E79"
        cor2 = (getattr(timbre, "rodape_cor_barra_inferior", None) if timbre else None) or "2E75B6"
        orgao = html_escape((getattr(timbre, "orgao_nome", None) if timbre else None) or "Orgao Publico")
        secretaria = html_escape((getattr(timbre, "secretaria_nome", None) if timbre else None) or "")

        cabecalho_tag = ""
        if timbre and getattr(timbre, "cabecalho_img", False):
            cabecalho_tag = (
                '<img src="data:image/png;base64,'
                + timbre.cabecalho_img
                + '" style="width:100%; max-height:120px; object-fit:contain; margin-bottom:6px;"/>'
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
<html><body style="margin:0; padding:2px 20px; border-top:2px solid #{cor2}; font-size:10px; color:#555;">
  {rodape_tag}
  <span>Gerado pelo Sistema AGI Gov</span>
  <span style="float:right;">Pagina <span class="page"></span> de <span class="topage"></span></span>
</body></html>
"""
        html_body = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <style>
    body {{ font-family: Arial, sans-serif; font-size: 12pt; line-height: 1.6; color: #222; }}
    h1, h2, h3 {{ color: #{cor1}; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 6px; }}
  </style>
</head>
<body>{content_html or ''}</body>
</html>"""
        return html_body, header_html, footer_html
