import pathlib

from odoo import fields


class GovTypstFramework:
    _PRESETS = {
        "dfd_padrao": {
            "label": "DFD Estruturado",
            "doc_type": "dfd",
            "title": "Documento de Formalizacao de Demanda",
            "subtitle": "Instrucao inicial da necessidade administrativa",
            "legal_basis": "Lei 14.133/2021, art. 12, VII, art. 18 e normativos locais aplicaveis.",
            "piece_keys": ("dfd",),
        },
        "etp_padrao": {
            "label": "ETP Estruturado",
            "doc_type": "etp",
            "title": "Estudo Tecnico Preliminar",
            "subtitle": "Analise tecnica da necessidade e da solucao",
            "legal_basis": "Lei 14.133/2021, art. 18 e regulamentos da fase preparatoria.",
            "piece_keys": ("etp",),
        },
        "tr_padrao": {
            "label": "TR Estruturado",
            "doc_type": "tr",
            "title": "Termo de Referencia",
            "subtitle": "Especificacao consolidada para contratacao",
            "legal_basis": "Lei 14.133/2021, fase preparatoria e matriz de responsabilidades do processo.",
            "piece_keys": ("tr",),
        },
        "despacho_padrao": {
            "label": "Despacho Administrativo",
            "doc_type": "despacho",
            "title": "Despacho Administrativo",
            "subtitle": "Manifestacao formal da autoridade ou unidade responsavel",
            "legal_basis": "Lei 14.133/2021 e fluxo interno do processo administrativo.",
            "piece_keys": ("despacho",),
        },
        "justificativa_emergencial": {
            "label": "Justificativa Emergencial",
            "doc_type": "outro",
            "title": "Justificativa de Situacao Emergencial",
            "subtitle": "Caracterizacao da urgencia e delimitacao do objeto necessario",
            "legal_basis": "Lei 14.133/2021, art. 75, VIII, com demonstracao objetiva do risco e da urgencia.",
            "piece_keys": ("justificativa",),
        },
        "nota_tecnica": {
            "label": "Nota Tecnica",
            "doc_type": "outro",
            "title": "Nota Tecnica",
            "subtitle": "Documento tecnico para instrucao do processo",
            "legal_basis": "Normativos internos, base legal do processo e fundamentos tecnicos do tema.",
            "piece_keys": ("nota_tecnica",),
        },
        "dispensa_emergencial": {
            "label": "Dispensa Emergencial",
            "doc_type": "outro",
            "title": "Processo de Dispensa Emergencial",
            "subtitle": "Capa, justificativa, ETP, despacho e ratificacao",
            "legal_basis": "Lei 14.133/2021, art. 75, VIII, com instrucao da fase preparatoria e publicacao posterior.",
            "piece_keys": ("justificativa", "etp", "despacho", "ratificacao"),
        },
    }
    _PIECES = (
        ("dfd", "DFD"),
        ("justificativa", "Justificativa"),
        ("etp", "ETP"),
        ("tr", "Termo de Referencia"),
        ("despacho", "Despacho"),
        ("ratificacao", "Ratificacao"),
        ("nota_tecnica", "Nota Tecnica"),
    )
    _FRAMEWORK_ROOT = pathlib.Path(__file__).resolve().parent / "typst_framework"

    @classmethod
    def get_model_selection(cls):
        return [(key, meta["label"]) for key, meta in cls._PRESETS.items()]

    @classmethod
    def get_defaults(cls, model_key):
        return dict(cls._PRESETS.get(model_key or "nota_tecnica", cls._PRESETS["nota_tecnica"]))

    @classmethod
    def get_piece_selection(cls):
        return list(cls._PIECES)

    @classmethod
    def get_piece_keys(cls, model_key):
        return list(cls.get_defaults(model_key).get("piece_keys") or ())

    @classmethod
    def build_document(cls, payload):
        piece_keys = cls._normalize_piece_keys(payload.get("piece_keys"))
        parts = [
            cls._read_framework_file("estilos.typ"),
            cls._read_framework_file("macros.typ"),
            cls._read_framework_file("processo.typ"),
        ]
        parts.extend(cls._read_framework_file(f"pecas/{piece_key}.typ") for piece_key in piece_keys)
        parts.append(cls._build_dados_block(payload))
        parts.append(cls._build_main_block(piece_keys))
        return "\n\n".join(part for part in parts if part).strip() + "\n"

    @classmethod
    def _read_framework_file(cls, relative_path):
        path = cls._FRAMEWORK_ROOT / relative_path
        return f"// framework:{relative_path}\n{path.read_text(encoding='utf-8').strip()}"

    @classmethod
    def _build_dados_block(cls, payload):
        custos = cls._build_cost_rows(payload.get("summary_lines"))
        data = {
            "municipio": payload.get("company_name") or "",
            "secretaria": payload.get("requesting_area") or "",
            "fundo": payload.get("process_scope_label") or "",
            "processo": payload.get("process_number") or "Novo",
            "modalidade": payload.get("title") or "Documento",
            "fundamento": payload.get("legal_basis") or "",
            "objeto": payload.get("object_text") or "",
            "valor": cls._extract_summary_value(payload.get("summary_lines"), "Valor estimado")
            or cls._extract_summary_value(payload.get("summary_lines"), "Valor global")
            or "",
            "local": payload.get("company_name") or "",
            "data": payload.get("generated_on") or fields.Date.today().strftime("%d/%m/%Y"),
            "responsavel": payload.get("responsible_name") or "",
            "natureza": cls._extract_summary_value(payload.get("summary_lines"), "Natureza de Despesa") or "",
            "fonte": cls._extract_summary_value(payload.get("summary_lines"), "Fonte") or "",
            "prefeito": payload.get("signer_name") or "",
            "necessidade": payload.get("justification_text") or payload.get("facts_text") or "",
            "referencia": payload.get("reference") or "",
            "titulo": payload.get("title") or "",
            "subtitulo": payload.get("subtitle") or "",
            "assunto": payload.get("process_subject") or "",
            "tipo_processo": payload.get("process_type_label") or "",
            "escopo_processo": payload.get("process_scope_label") or "",
            "fatos_relevantes": payload.get("facts_text") or "",
            "pontos_chave": payload.get("key_points_text") or "",
            "encaminhamento": payload.get("routing_text") or "",
            "observacoes_finais": payload.get("closing_notes") or "",
            "assinante_nome": payload.get("signer_name") or "",
            "assinante_cargo": payload.get("signer_role") or "",
        }
        lines = ["#let dados = ("]
        for key, value in data.items():
            lines.append(f"  {key}: {cls._serialize_value(value)},")
        lines.append(f"  custos: {cls._serialize_costs(custos)},")
        lines.append(")")
        return "\n".join(lines)

    @classmethod
    def _build_main_block(cls, piece_keys):
        piece_calls = ",\n    ".join(f"{piece_key}(dados)" for piece_key in piece_keys)
        return (
            "#processo_admin(\n"
            "  dados: dados,\n"
            "  pecas: (\n"
            f"    {piece_calls}\n"
            "  )\n"
            ")"
        )

    @classmethod
    def _normalize_piece_keys(cls, piece_keys):
        valid_keys = {key for key, _label in cls._PIECES}
        normalized = []
        for key in piece_keys or ():
            if key in valid_keys and key not in normalized:
                normalized.append(key)
        return normalized or ["nota_tecnica"]

    @classmethod
    def _build_cost_rows(cls, summary_lines):
        rows = []
        for index, (label, value) in enumerate(cls._parse_pairs(summary_lines), start=1):
            rows.append({"grupo": str(index), "descricao": label, "valor": value})
        return rows

    @classmethod
    def _extract_summary_value(cls, summary_lines, expected_label):
        expected = (expected_label or "").strip().lower()
        for label, value in cls._parse_pairs(summary_lines):
            if label.strip().lower() == expected:
                return value
        return ""

    @classmethod
    def _parse_pairs(cls, text):
        pairs = []
        for raw_line in (text or "").splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                pairs.append((key, value))
        return pairs

    @classmethod
    def _serialize_costs(cls, rows):
        if not rows:
            return "()"
        formatted_rows = []
        for row in rows:
            formatted_rows.append(
                "(\n"
                f'    grupo: "{cls._escape_string(row["grupo"])}",\n'
                f'    descricao: "{cls._escape_string(row["descricao"])}",\n'
                f'    valor: "{cls._escape_string(row["valor"])}",\n'
                "  )"
            )
        return "(\n  " + ",\n  ".join(formatted_rows) + "\n)"

    @classmethod
    def _serialize_value(cls, value):
        if value is None:
            return '""'
        if isinstance(value, bool):
            return "true" if value else "false"
        text = str(value).strip()
        if not text:
            return '""'
        return f'"{cls._escape_string(text)}"'

    @classmethod
    def _escape_string(cls, value):
        return (
            str(value)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\r", "")
            .replace("\n", "\\n")
        )
