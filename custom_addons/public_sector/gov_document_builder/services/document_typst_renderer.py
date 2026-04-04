import json
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class GovDocumentTypstRenderer(models.AbstractModel):
    """Compila o layout canonico do documento em codigo Typst."""

    _name = "gov.document.typst.renderer"
    _description = "Compilador JSON/AST → Typst"

    def render_instance(self, instance):
        """
        Ponto de entrada principal.
        Retorna string com o código Typst completo do documento.
        """
        resolver = self.env["gov.document.context.resolver"]
        context = resolver.resolve_instance_context(instance)
        return self._render_layout(instance, instance.layout_json, context)

    def render_version(self, version):
        """Renderiza uma versão persistida recompondo apenas os namespaces dinâmicos."""
        resolver = self.env["gov.document.context.resolver"]
        instance = version.document_instance_id
        try:
            snapshot_context = json.loads(version.resolved_context_json or "{}")
        except json.JSONDecodeError:
            snapshot_context = {}
        try:
            dynamic_namespaces = json.loads(version.dynamic_namespaces_json or "[]")
        except json.JSONDecodeError:
            dynamic_namespaces = []
        snapshot_context.pop("dynamic_namespaces", None)

        current_context = resolver.resolve_instance_context(instance)
        merged_context = dict(snapshot_context)
        for namespace in dynamic_namespaces:
            if namespace == "reconciliation":
                continue
            if namespace in current_context:
                merged_context[namespace] = current_context[namespace]

        if "document" not in merged_context:
            merged_context["document"] = current_context.get("document", {})
        if "institution" not in merged_context:
            merged_context["institution"] = current_context.get("institution", {})
        if "reconciliation" in dynamic_namespaces or "reconciliation" not in merged_context:
            merged_context["reconciliation"] = resolver.compute_reconciliation_namespace(
                merged_context
            )

        return self._render_layout(instance, version.layout_json, merged_context)

    def _render_layout(self, instance, layout_json, context):
        normalizer = self.env["gov.document.layout.normalizer"]
        nodes = normalizer.normalize(layout_json)
        errors = normalizer.validate(nodes)
        if errors:
            _logger.warning(
                "gov_document_builder: erros de validação em %s: %s",
                instance.id,
                errors,
            )
        lines = []
        lines += self._render_preamble(instance, context)
        lines.append("")
        for node in nodes:
            rendered = self._render_node(node, context)
            if rendered is not None:
                lines.append(rendered)
                lines.append("")
        return "\n".join(lines)

    def _render_preamble(self, instance, context):
        template = instance.template_id
        preamble = template.typst_preamble if template else ""
        doc_name = instance.name or "Documento"
        process_no = context.get("process", {}).get("number", "")
        return [
            "// Gerado por gov_document_builder — Kodoo/GRP",
            f"// Instância: {instance.id} · {doc_name}",
            "",
            '#import "base.typ": semsa_doc',
            '#import "law_14133.typ": artigo, base_legal_box',
            "",
            "#show: semsa_doc(",
            f'  title: "{doc_name}",',
            f'  process_no: "{process_no}"',
            ")",
            preamble or "",
        ]

    def _render_node(self, node, context):
        """Dispatcher por tipo de bloco."""
        resolver = self.env["gov.document.context.resolver"]
        visibility_rule = node.get("visibility_rule")
        if visibility_rule and not resolver.evaluate_visibility_rule(visibility_rule, context):
            return None

        renderers = {
            "heading": self._render_heading,
            "heading1": self._render_heading,
            "heading2": self._render_heading2,
            "conditional": self._render_conditional,
            "legal_basis": self._render_legal_basis,
            "process_field": self._render_process_field,
            "process_header": self._render_process_header,
            "rich_text": self._render_rich_text,
            "richtext": self._render_rich_text,
            "signature": self._render_signature,
            "table": self._render_table,
            "quadro_resumo": self._render_quadro_resumo,
            "divider": self._render_divider,
            "bullet_list": self._render_bullet_list,
            "metadata": self._render_metadata,
            "sumario": self._render_sumario,
        }
        renderer = renderers.get(node["type"])
        if not renderer:
            return f'// [bloco não renderizado: {node["type"]}]'
        try:
            return renderer(node, context)
        except Exception as error:
            _logger.error(
                "gov_document_builder: erro ao renderizar nó %s: %s",
                node.get("id"),
                error,
            )
            return f'// [erro ao renderizar {node["type"]}]'

    def _render_heading(self, node, context):
        text = node["props"].get("text", "Título")
        level = node["props"].get("level", 1)
        return f'{"=" * level} {text}'

    def _render_heading2(self, node, context):
        text = node["props"].get("text", "Seção")
        return f"== {text}"

    def _render_conditional(self, node, context):
        rendered_children = []
        for child in node.get("children", []):
            rendered = self._render_node(child, context)
            if rendered is not None:
                rendered_children.append(rendered)
        return "\n".join(rendered_children)

    def _render_legal_basis(self, node, context):
        return '#base_legal_box[\n  #artigo("Lei 14.133/2021", "art. 18")\n]'

    def _render_process_field(self, node, context):
        label = node["props"].get("label", "Campo")
        binding = node.get("binding", {})
        resolver = self.env["gov.document.context.resolver"]
        value = resolver.resolve_binding(binding, context) if binding else ""
        return f"*{label}:* {value}"

    def _render_process_header(self, node, context):
        proc = context.get("process", {})
        lines = ["#process_header("]
        for key, value in proc.items():
            lines.append(f'  {key}: "{value}",')
        lines.append(")")
        return "\n".join(lines)

    def _render_rich_text(self, node, context):
        content = node["props"].get("content", "")
        return content if content else "// [parágrafo vazio]"

    def _render_signature(self, node, context):
        return "#signature_block(context.signatories)"

    def _render_table(self, node, context):
        return "#table_block(context)"

    def _render_quadro_resumo(self, node, context):
        return "#quadro_resumo(context.process)"

    def _render_divider(self, node, context):
        return "#line(length: 100%)"

    def _render_bullet_list(self, node, context):
        items = node["props"].get("items", [])
        if not items:
            return "// [lista vazia]"
        return "\n".join(f"- {item}" for item in items)

    def _render_metadata(self, node, context):
        inst = context.get("institution", {})
        doc = context.get("document", {})
        return f'{inst.get("city", "")}/{inst.get("state", "")}, {doc.get("date", "")}'

    def _render_sumario(self, node, context):
        props = node.get("props", {})
        title = props.get("titulo") or "Sumário"
        try:
            depth = int(props.get("profundidade") or 2)
        except (TypeError, ValueError):
            depth = 2
        depth = max(1, min(depth, 2))
        show_numbers = props.get("mostrar_numeros", True)

        outline_line = f"#outline(title: [{title}], depth: {depth})"
        if show_numbers:
            return outline_line

        return "\n".join(
            [
                "#set outline.entry(fill: none)",
                "#show outline.entry: it => link(",
                "  it.element.location(),",
                "  it.indented(it.prefix(), it.body()),",
                ")",
                outline_line,
            ]
        )
