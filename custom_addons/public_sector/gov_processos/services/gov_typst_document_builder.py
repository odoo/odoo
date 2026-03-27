from odoo import fields

from odoo.addons.gov_processos.models.gov_template_service import GovTemplateService


class GovTypstDocumentBuilder:
    _MODEL_META = {
        "dfd_padrao": {
            "label": "DFD Estruturado",
            "doc_type": "dfd",
            "title": "Documento de Formalizacao de Demanda",
            "subtitle": "Instrucao inicial da necessidade administrativa",
            "legal_basis": "Lei 14.133/2021, art. 12, VII, art. 18 e normativos locais aplicaveis.",
        },
        "etp_padrao": {
            "label": "ETP Estruturado",
            "doc_type": "etp",
            "title": "Estudo Tecnico Preliminar",
            "subtitle": "Analise tecnica da necessidade e da solucao",
            "legal_basis": "Lei 14.133/2021, art. 18 e regulamentos da fase preparatoria.",
        },
        "tr_padrao": {
            "label": "TR Estruturado",
            "doc_type": "tr",
            "title": "Termo de Referencia",
            "subtitle": "Especificacao consolidada para contratacao",
            "legal_basis": "Lei 14.133/2021, fase preparatoria e matriz de responsabilidades do processo.",
        },
        "despacho_padrao": {
            "label": "Despacho Administrativo",
            "doc_type": "despacho",
            "title": "Despacho Administrativo",
            "subtitle": "Manifestacao formal da autoridade ou unidade responsavel",
            "legal_basis": "Lei 14.133/2021 e fluxo interno do processo administrativo.",
        },
        "justificativa_emergencial": {
            "label": "Justificativa Emergencial",
            "doc_type": "outro",
            "title": "Justificativa de Situacao Emergencial",
            "subtitle": "Caracterizacao da urgencia e delimitacao do objeto necessario",
            "legal_basis": "Lei 14.133/2021, art. 75, VIII, com demonstracao objetiva do risco e da urgencia.",
        },
        "nota_tecnica": {
            "label": "Nota Tecnica",
            "doc_type": "outro",
            "title": "Nota Tecnica",
            "subtitle": "Documento tecnico para instrucao do processo",
            "legal_basis": "Normativos internos, base legal do processo e fundamentos tecnicos do tema.",
        },
    }

    @classmethod
    def get_model_selection(cls):
        return [(key, meta["label"]) for key, meta in cls._MODEL_META.items()]

    @classmethod
    def get_defaults(cls, model_key):
        return dict(cls._MODEL_META.get(model_key or "nota_tecnica", cls._MODEL_META["nota_tecnica"]))

    @classmethod
    def get_default_doc_type(cls, model_key):
        return cls.get_defaults(model_key).get("doc_type", "outro")

    @classmethod
    def get_default_title(cls, model_key):
        return cls.get_defaults(model_key).get("title", "Documento")

    @classmethod
    def build_document(cls, payload):
        title = cls._escape(payload.get("title") or "Documento")
        subtitle = cls._escape(payload.get("subtitle") or "")
        legal_basis = cls._escape(payload.get("legal_basis") or "")
        process_number = cls._escape(payload.get("process_number") or "Novo")
        process_subject = cls._escape(payload.get("process_subject") or "")
        process_type = cls._escape(payload.get("process_type_label") or "")
        process_scope = cls._escape(payload.get("process_scope_label") or "")
        company = cls._escape(payload.get("company_name") or "")
        reference = cls._escape(payload.get("reference") or "")
        area = cls._escape(payload.get("requesting_area") or "")
        responsible = cls._escape(payload.get("responsible_name") or "")
        signer_name = cls._escape(payload.get("signer_name") or "")
        signer_role = cls._escape(payload.get("signer_role") or "")
        generated_on = cls._escape(payload.get("generated_on") or fields.Date.today().strftime("%d/%m/%Y"))

        summary_pairs = [
            ("Processo", process_number),
            ("UG", company),
            ("Tipo do processo", process_type),
            ("Escopo", process_scope),
            ("Area requisitante", area),
            ("Responsavel", responsible),
            ("Referencia", reference),
            ("Base legal", legal_basis),
            ("Gerado em", generated_on),
        ]
        summary_pairs.extend(cls._parse_pairs(payload.get("summary_lines")))
        summary_block = cls._render_pairs(summary_pairs)

        sections = [
            ("Objeto", payload.get("object_text")),
            ("Justificativa", payload.get("justification_text")),
            ("Fatos Relevantes", payload.get("facts_text")),
            ("Pontos-Chave", payload.get("key_points_text"), "bullets"),
            ("Encaminhamento", payload.get("routing_text")),
            ("Observacoes Finais", payload.get("closing_notes")),
        ]
        section_blocks = []
        for item in sections:
            title_text = item[0]
            body_text = item[1]
            mode = item[2] if len(item) > 2 else "paragraphs"
            rendered = cls._render_section(title_text, body_text, mode=mode)
            if rendered:
                section_blocks.append(rendered)

        signature_block = ""
        if payload.get("include_signature"):
            signature_block = cls._render_signature_block(
                signer_name=signer_name,
                signer_role=signer_role,
                company=company,
                generated_on=generated_on,
            )

        legal_box = cls._render_highlight_box("Base Legal", legal_basis, color="c-green") if legal_basis else ""
        subject_box = (
            cls._render_highlight_box("Assunto do Processo", process_subject, color="c-blue")
            if process_subject
            else ""
        )

        body_parts = [
            cls._base_style(),
            cls._render_cover(
                title=title,
                subtitle=subtitle,
                company=company,
                process_number=process_number,
                generated_on=generated_on,
            ),
            "#pagebreak()",
            '#outline(title: text(size: 15pt, weight: "bold", fill: c-navy)[Sumario], depth: 2)',
            "#pagebreak()",
            "= Identificacao do Documento",
            summary_block,
            legal_box,
            subject_box,
        ]
        body_parts.extend(section_blocks)
        if signature_block:
            body_parts.extend(["= Assinatura", signature_block])
        return "\n\n".join(part for part in body_parts if part).strip() + "\n"

    @classmethod
    def _base_style(cls):
        return """
#let c-navy = rgb("#16324A")
#let c-blue = rgb("#2D6E9F")
#let c-soft = rgb("#6B7D8D")
#let c-line = rgb("#D9E4EC")
#let c-stripe = rgb("#F5F8FB")
#let c-green = rgb("#1D6A4F")

#set document(author: "AGI Gov")
#set page(
  paper: "a4",
  margin: (top: 2.6cm, bottom: 2.4cm, left: 2.6cm, right: 2.4cm),
  header: context {
    if counter(page).get().first() > 1 [
      #grid(
        columns: (1fr, auto),
        [#set text(size: 8.5pt, weight: "semibold", fill: c-navy) #header-title],
        [#set text(size: 8pt, fill: c-soft) Processo #header-process],
      )
      #v(4pt)
      #line(length: 100%, stroke: (paint: c-line, thickness: 0.7pt))
    ]
  },
  footer: context {
    if counter(page).get().first() > 1 [
      #line(length: 100%, stroke: (paint: c-line, thickness: 0.5pt))
      #v(4pt)
      #align(center)[
        #set text(size: 8pt, fill: c-soft)
        Pagina #counter(page).display() de #counter(page).final().first()
      ]
    ]
  },
)

#set text(size: 10.5pt, lang: "pt", fallback: true)
#set par(justify: true, leading: 0.72em, spacing: 0.95em)
#set list(indent: 1.3em, body-indent: 0.4em, spacing: 0.4em)

#show heading.where(level: 1): it => block(above: 1.4em, below: 0.5em)[
  #text(size: 12pt, weight: "semibold", fill: c-navy)[#it.body]
  #line(length: 100%, stroke: (paint: c-blue, thickness: 0.8pt))
]

#let ficha(..rows) = {
  let values = rows.pos()
  block(
    width: 100%,
    stroke: (paint: c-line, thickness: 0.6pt),
    radius: 4pt,
    clip: true,
  )[
    #for (idx, row) in values.enumerate() {
      #grid(
        columns: (4.5cm, 1fr),
        column-gutter: 8pt,
        block(
          width: 100%,
          fill: if calc.odd(idx) { c-stripe } else { white },
          inset: (x: 10pt, y: 7pt),
        )[
          #set text(size: 9pt, weight: "semibold", fill: c-navy)
          #row.at(0)
        ],
        block(
          width: 100%,
          inset: (x: 10pt, y: 7pt),
        )[
          #set text(size: 9.2pt)
          #row.at(1)
        ],
      )
      #if idx < values.len() - 1 [
        #line(length: 100%, stroke: (paint: c-line, thickness: 0.45pt))
      ]
    }
  ]
}

#let destaque(title, color, body) = block(
  width: 100%,
  fill: color.lighten(92%),
  stroke: (left: (paint: color, thickness: 4pt)),
  inset: (left: 12pt, right: 10pt, top: 10pt, bottom: 10pt),
  radius: (right: 3pt),
)[
  #text(size: 9pt, weight: "semibold", fill: color)[#title]
  #v(4pt)
  #body
]
""".strip()

    @classmethod
    def _render_cover(cls, title, subtitle, company, process_number, generated_on):
        subtitle_line = f'#text(size: 11pt, fill: rgb("#BFD7E6"))[{subtitle}]' if subtitle else ""
        return f"""
#let header-title = "{title}"
#let header-process = "{process_number}"

#page(
  header: none,
  footer: none,
  margin: (top: 0pt, bottom: 0pt, left: 0pt, right: 0pt),
  background: rect(fill: c-navy, width: 100%, height: 100%),
)[
  #set text(fill: white)
  #pad(left: 2.8cm, right: 2.8cm, top: 2.6cm, bottom: 2.4cm)[
    #text(size: 9pt, tracking: 0.8pt, fill: rgb("#A7C6DA"))[{company}]
    #v(1.1cm)
    #text(size: 24pt, weight: "bold")[{title}]
    #v(8pt)
    {subtitle_line}
    #v(0.9cm)
    #line(length: 100%, stroke: (paint: white.transparentize(55%), thickness: 0.8pt))
    #v(0.9cm)
    #grid(
      columns: (auto, 1fr),
      column-gutter: 10pt,
      row-gutter: 8pt,
      text(size: 9pt, fill: rgb("#A7C6DA"), weight: "semibold")[Processo],
      text(size: 10pt)[{process_number}],
      text(size: 9pt, fill: rgb("#A7C6DA"), weight: "semibold")[Gerado em],
      text(size: 10pt)[{generated_on}],
    )
    #v(1fr)
    #align(right)[
      #text(size: 8.5pt, fill: rgb("#BFD7E6"))[Documento estruturado em Typst]
    ]
  ]
)]
""".strip()

    @classmethod
    def _render_pairs(cls, pairs):
        clean = [(label, value) for label, value in pairs if value]
        if not clean:
            return ""
        rows = ",\n  ".join(f'("{label}", "{value}")' for label, value in clean)
        return f"#ficha(\n  {rows},\n)"

    @classmethod
    def _render_highlight_box(cls, title, body, color="c-blue"):
        if not body:
            return ""
        rendered_body = cls._render_paragraphs(body)
        return f'#destaque("{title}", {color})[\n{rendered_body}\n]'

    @classmethod
    def _render_section(cls, title, body, mode="paragraphs"):
        if not (body or "").strip():
            return ""
        if mode == "bullets":
            rendered = cls._render_bullets(body)
        else:
            rendered = cls._render_paragraphs(body)
        if not rendered:
            return ""
        return f"= {cls._escape(title)}\n\n{rendered}"

    @classmethod
    def _render_paragraphs(cls, text):
        paragraphs = []
        for block in cls._split_blocks(text):
            paragraphs.append(cls._escape(block))
        return "\n\n".join(paragraphs)

    @classmethod
    def _render_bullets(cls, text):
        items = []
        for raw in (text or "").splitlines():
            clean = raw.strip().lstrip("-*+").strip()
            if clean:
                items.append(f"+ {cls._escape(clean)}")
        return "\n".join(items)

    @classmethod
    def _render_signature_block(cls, signer_name, signer_role, company, generated_on):
        signer_name = signer_name or "Responsavel"
        signer_role = signer_role or ""
        company = company or ""
        lines = [generated_on, company, "", "_______________________________", signer_name]
        if signer_role:
            lines.append(signer_role)
        return "\n".join(cls._escape(line) if line else "" for line in lines)

    @classmethod
    def _parse_pairs(cls, raw_text):
        pairs = []
        for line in (raw_text or "").splitlines():
            clean = line.strip()
            if not clean or ":" not in clean:
                continue
            label, value = clean.split(":", 1)
            label = cls._escape(label.strip())
            value = cls._escape(value.strip())
            if label and value:
                pairs.append((label, value))
        return pairs

    @classmethod
    def _split_blocks(cls, text):
        return [
            " ".join(piece.strip() for piece in block.splitlines() if piece.strip())
            for block in (text or "").strip().split("\n\n")
            if block.strip()
        ]

    @classmethod
    def _escape(cls, value):
        return GovTemplateService.escape_typst(value or "").replace('"', '\\"')
