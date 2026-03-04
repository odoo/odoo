import base64
import io
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

try:
    from PIL import Image

    _PIL_AVAILABLE = True
except Exception:
    _PIL_AVAILABLE = False

CABECALHO_MAX_BYTES = 500 * 1024
RODAPE_MAX_BYTES = 300 * 1024
CABECALHO_MAX_WIDTH = 800
CABECALHO_MAX_HEIGHT = 200
RODAPE_MAX_WIDTH = 800
RODAPE_MAX_HEIGHT = 100
CABECALHO_ALTURA_DEFAULT = 3.0
RODAPE_ALTURA_DEFAULT = 1.5


class GovTimbre(models.Model):
    _name = "gov.timbre"
    _description = "Timbre Institucional"
    _order = "ug_id, name"

    name = fields.Char(
        string="Nome do Timbre",
        required=True,
        help="Ex: Timbre Oficial 2026, Timbre Simplificado",
    )
    ug_id = fields.Many2one(
        "res.company",
        string="UG / Orgao",
        required=True,
        default=lambda self: self.env.company,
    )
    is_default = fields.Boolean(
        string="Padrao para esta UG",
        default=False,
    )
    active = fields.Boolean(default=True)

    cabecalho_img = fields.Binary(
        string="Imagem do Cabecalho",
        help=(
            "PNG ou JPG. Largura: ate 800px. "
            "Altura recomendada: ate 200px. Max: 500KB."
        ),
    )
    cabecalho_img_fname = fields.Char("Nome do arquivo - Cabecalho")
    cabecalho_altura = fields.Float(
        string="Altura reservada (cm)",
        default=CABECALHO_ALTURA_DEFAULT,
        help="Altura em cm reservada para o cabecalho no PDF. Padrao: 3.0 cm.",
    )

    rodape_img = fields.Binary(
        string="Imagem do Rodape",
        help=(
            "PNG ou JPG. Largura: ate 800px. "
            "Altura recomendada: ate 100px. Max: 300KB."
        ),
    )
    rodape_img_fname = fields.Char("Nome do arquivo - Rodape")
    rodape_altura = fields.Float(
        string="Altura reservada - rodape (cm)",
        default=RODAPE_ALTURA_DEFAULT,
        help="Altura em cm reservada para o rodape no PDF. Padrao: 1.5 cm.",
    )

    orgao_nome = fields.Char(
        string="Nome do Orgao (fallback)",
        help="Usado quando a imagem de cabecalho nao esta disponivel.",
    )
    secretaria_nome = fields.Char(string="Nome da Secretaria (fallback)")
    cnpj = fields.Char(string="CNPJ (fallback)", size=18)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_default"):
                ug_id = vals.get("ug_id") or self.env.company.id
                conflitos = self.search(
                    [
                        ("ug_id", "=", ug_id),
                        ("is_default", "=", True),
                        ("active", "=", True),
                    ]
                ).filtered(lambda t: not t._is_legacy_seed_default())
                if conflitos:
                    raise ValidationError(
                        "Ja existe um timbre padrao para esta UG: "
                        f"{conflitos[0].name}."
                    )
        records = super().create(vals_list)
        records._demote_legacy_seed_default()
        return records

    def write(self, vals):
        if vals.get("is_default"):
            for rec in self:
                ug_id = vals.get("ug_id", rec.ug_id.id)
                conflitos = self.search(
                    [
                        ("ug_id", "=", ug_id),
                        ("is_default", "=", True),
                        ("id", "!=", rec.id),
                        ("active", "=", True),
                    ]
                ).filtered(lambda t: not t._is_legacy_seed_default())
                if conflitos:
                    raise ValidationError(
                        "Ja existe um timbre padrao para esta UG: "
                        f"{conflitos[0].name}."
                    )
        res = super().write(vals)
        if vals.get("is_default"):
            self._demote_legacy_seed_default()
        return res

    @api.constrains("is_default", "ug_id")
    def _check_unique_default(self):
        for rec in self:
            if not rec.is_default:
                continue
            outros = self.search(
                [
                    ("ug_id", "=", rec.ug_id.id),
                    ("is_default", "=", True),
                    ("id", "!=", rec.id),
                    ("active", "=", True),
                ]
            )
            outros_reais = outros.filtered(lambda t: not t._is_legacy_seed_default())
            if outros_reais:
                raise ValidationError(
                    "Ja existe um timbre padrao para "
                    f"{rec.ug_id.name}: {outros_reais[0].name}. "
                    "Desmarque-o antes de definir um novo padrao."
                )

    def _demote_legacy_seed_default(self):
        for rec in self.filtered("is_default"):
            outros = self.search(
                [
                    ("ug_id", "=", rec.ug_id.id),
                    ("is_default", "=", True),
                    ("id", "!=", rec.id),
                    ("active", "=", True),
                ]
            )
            legacy = outros.filtered(lambda t: t._is_legacy_seed_default())
            if legacy:
                legacy.write({"is_default": False})

    def _is_legacy_seed_default(self):
        self.ensure_one()
        try:
            xmlid = self.get_external_id().get(self.id)
            return xmlid == "gov_processos.timbre_padrao_grp"
        except Exception:
            return False

    @api.constrains("cabecalho_altura", "rodape_altura")
    def _check_alturas(self):
        for rec in self:
            if rec.cabecalho_altura <= 0:
                raise ValidationError("A altura do cabecalho deve ser maior que zero.")
            if rec.rodape_altura <= 0:
                raise ValidationError("A altura do rodape deve ser maior que zero.")

    @api.constrains("cabecalho_img")
    def _check_cabecalho_size(self):
        for rec in self:
            if not rec.cabecalho_img:
                continue
            rec._validate_image(
                rec.cabecalho_img,
                max_bytes=CABECALHO_MAX_BYTES,
                max_width=CABECALHO_MAX_WIDTH,
                max_height=CABECALHO_MAX_HEIGHT,
                label="cabecalho",
            )

    @api.constrains("rodape_img")
    def _check_rodape_size(self):
        for rec in self:
            if not rec.rodape_img:
                continue
            rec._validate_image(
                rec.rodape_img,
                max_bytes=RODAPE_MAX_BYTES,
                max_width=RODAPE_MAX_WIDTH,
                max_height=RODAPE_MAX_HEIGHT,
                label="rodape",
            )

    def _validate_image(self, b64_data, max_bytes, max_width, max_height, label):
        try:
            raw = base64.b64decode(b64_data)
        except Exception as exc:
            raise ValidationError(f"Imagem de {label} invalida.") from exc

        size = len(raw)
        if size > max_bytes:
            raise ValidationError(
                f"Imagem do {label} excede o limite de {max_bytes // 1024} KB "
                f"({size // 1024} KB enviados)."
            )

        if raw.startswith(b"\x89PNG\r\n\x1a\n"):
            fmt = "png"
        elif raw.startswith(b"\xff\xd8\xff"):
            fmt = "jpg"
        else:
            raise ValidationError(
                f"Formato da imagem de {label} invalido. "
                "Use PNG ou JPG."
            )

        if _PIL_AVAILABLE:
            try:
                with Image.open(io.BytesIO(raw)) as img:
                    width, height = img.size
                if width > max_width or height > max_height:
                    raise ValidationError(
                        f"Imagem de {label} fora do limite {max_width}x{max_height}px. "
                        f"Recebido: {width}x{height}px."
                    )
            except ValidationError:
                raise
            except Exception as exc:
                _logger.warning(
                    "Falha ao validar dimensoes da imagem %s (formato %s): %s",
                    label,
                    fmt,
                    exc,
                )

    @api.model
    def get_default_for_company(self, company_id):
        timbre = self.search(
            [
                ("ug_id", "=", company_id),
                ("is_default", "=", True),
                ("active", "=", True),
            ],
            limit=1,
        )
        if timbre:
            return timbre
        timbre = self.search(
            [("ug_id", "=", company_id), ("active", "=", True)],
            limit=1,
        )
        return timbre or None

    def get_latex_cabecalho(self):
        self.ensure_one()
        altura = self.cabecalho_altura or CABECALHO_ALTURA_DEFAULT
        if self.cabecalho_img:
            return (
                r"\begin{center}"
                + rf"\IfFileExists{{cabecalho}}{{\includegraphics[width=\textwidth,height={altura}cm,keepaspectratio]{{cabecalho}}}}{{}}"
                + r"\end{center}"
                + r"\vspace{0.3cm}"
            )

        orgao = self._escape_latex(self.orgao_nome or self.ug_id.name)
        secretaria = self._escape_latex(self.secretaria_nome or "")
        cnpj = self._escape_latex(self.cnpj or "")
        linhas = [r"\begin{center}", rf"  {{\large\bfseries {orgao}}} \\[0.2cm]"]
        if secretaria:
            linhas.append(rf"  {{\normalsize {secretaria}}} \\[0.1cm]")
        if cnpj:
            linhas.append(rf"  {{\small CNPJ: {cnpj}}} \\[0.2cm]")
        linhas.extend([r"\end{center}", r"\vspace{0.3cm}"])
        return "\n".join(linhas)

    def get_latex_rodape(self):
        self.ensure_one()
        altura = self.rodape_altura or RODAPE_ALTURA_DEFAULT
        if self.rodape_img:
            return (
                r"\begin{center}"
                + rf"\IfFileExists{{rodape}}{{\includegraphics[width=\textwidth,height={altura}cm,keepaspectratio]{{rodape}}}}{{}}"
                + r"\end{center}"
            )

        orgao = self._escape_latex(self.orgao_nome or self.ug_id.name)
        return (
            r"\begin{center}"
            + rf"{{\small\color{{gray}} {orgao}}}"
            + r"\end{center}"
        )

    def get_imagens_para_latex(self):
        self.ensure_one()
        return {
            "cabecalho": base64.b64decode(self.cabecalho_img) if self.cabecalho_img else None,
            "rodape": base64.b64decode(self.rodape_img) if self.rodape_img else None,
        }

    @staticmethod
    def _escape_latex(text):
        if not text:
            return ""
        replacements = [
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
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text
