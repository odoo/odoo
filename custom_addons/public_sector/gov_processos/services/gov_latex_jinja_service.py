"""
GovLatexJinjaService - Motor de renderizacao LaTeX via Jinja2.

Substitui a geracao de strings manuais (f-strings) nos wizards.
Os templates .tex.j2 ficam em services/latex_templates/.
"""
import os
import pathlib
import shutil
import subprocess
import tempfile
import uuid

import jinja2
from odoo.exceptions import UserError

_TEMPLATE_DIR = pathlib.Path(__file__).resolve().parent / "latex_templates"


def _make_jinja_env():
    loader = jinja2.FileSystemLoader(str(_TEMPLATE_DIR), encoding="utf-8")
    env = jinja2.Environment(
        loader=loader,
        autoescape=False,
        keep_trailing_newline=True,
        undefined=jinja2.Undefined,
    )
    # Helper: escapa caracteres especiais LaTeX
    def esc(text):
        if not text:
            return ""
        txt = str(text)
        for old, new in [
            ("\\", r"\textbackslash{}"),
            ("&", r"\&"),
            ("%", r"\%"),
            ("$", r"\$"),
            ("#", r"\#"),
            ("{", r"\{"),
            ("}", r"\}"),
            ("~", r"\textasciitilde{}"),
            ("^", r"\textasciicircum{}"),
            ("_", r"\_"),
        ]:
            txt = txt.replace(old, new)
        return txt

    env.filters["esc"] = esc
    env.globals["esc"] = esc
    return env


_JINJA_ENV = _make_jinja_env()


class GovLatexJinjaService:
    """
    Renderiza templates LaTeX Jinja2 e compila via pdflatex.

    Uso:
        source = GovLatexJinjaService.render("relatorio.tex.j2", ctx)
        pdf    = GovLatexJinjaService.compile(source, extra_images={...})
    """

    @classmethod
    def render(cls, template_name, context):
        """Renderiza um template .tex.j2 com o contexto fornecido."""
        try:
            tpl = _JINJA_ENV.get_template(template_name)
        except jinja2.TemplateNotFound as exc:
            raise UserError(
                f"Template LaTeX nao encontrado: {template_name}"
            ) from exc
        try:
            return tpl.render(**context)
        except jinja2.TemplateError as exc:
            raise UserError(
                f"Erro ao renderizar template LaTeX '{template_name}': {exc}"
            ) from exc

    @classmethod
    def compile(
        cls,
        latex_source,
        logo_binary=None,
        extra_images=None,
        timeout=120,
        two_passes=False,
    ):
        """
        Compila fonte LaTeX em PDF e retorna bytes.

        two_passes: use True apenas quando o documento tiver longtable ou
                    referencias cruzadas que precisam de uma segunda passagem.
        """
        pdflatex_path = shutil.which("pdflatex")
        if not pdflatex_path:
            raise UserError(
                "pdflatex nao encontrado no servidor. "
                "Instale TeX Live para habilitar a compilacao."
            )

        source = (latex_source or "").strip()
        if not source:
            raise UserError("Nenhum conteudo LaTeX para compilar.")

        tmp_dir = tempfile.mkdtemp(
            prefix=f"gov_latex_{uuid.uuid4().hex[:8]}_"
        )
        try:
            tex_path = os.path.join(tmp_dir, "main.tex")
            with open(tex_path, "w", encoding="utf-8") as fh:
                fh.write(source)

            if logo_binary:
                cls._save_image(tmp_dir, "logo", logo_binary)

            for nome, dados in (extra_images or {}).items():
                if dados:
                    cls._save_image(tmp_dir, nome, dados)

            passes = 2 if two_passes else 1
            for passagem in range(passes):
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
                        with open(
                            log_path, "r", encoding="utf-8", errors="replace"
                        ) as lf:
                            log_tail = "\n".join(
                                lf.read().splitlines()[-40:]
                            )
                    erros = [
                        line
                        for line in stdout.splitlines()
                        if line.startswith("!")
                    ]
                    msg = (
                        "\n".join(erros[:10])
                        or log_tail
                        or stderr
                        or stdout[-600:]
                    )
                    raise UserError(
                        f"Erro na compilacao LaTeX"
                        f" (passagem {passagem + 1}):\n\n{msg}"
                    )

            pdf_path = os.path.join(tmp_dir, "main.pdf")
            if not os.path.exists(pdf_path):
                raise UserError(
                    "PDF nao foi gerado. Verifique o codigo LaTeX."
                )
            with open(pdf_path, "rb") as fh:
                return fh.read()

        except subprocess.TimeoutExpired as exc:
            raise UserError(
                f"Compilacao LaTeX excedeu {timeout}s. "
                "Verifique se o documento nao possui processamento excessivo."
            ) from exc
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    @classmethod
    def render_and_compile(
        cls,
        template_name,
        context,
        logo_binary=None,
        extra_images=None,
        timeout=120,
        two_passes=False,
    ):
        """Conveniencia: render + compile em uma so chamada."""
        source = cls.render(template_name, context)
        return cls.compile(
            source,
            logo_binary=logo_binary,
            extra_images=extra_images,
            timeout=timeout,
            two_passes=two_passes,
        )

    @staticmethod
    def _save_image(tmp_dir, name, data):
        ext = "jpg" if data[:3] == b"\xff\xd8\xff" else "png"
        for filename in (f"{name}.{ext}", name):
            with open(os.path.join(tmp_dir, filename), "wb") as fh:
                fh.write(data)
