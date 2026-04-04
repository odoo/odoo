import json

from odoo import http
from odoo.http import request


class DocumentBuilderController(http.Controller):
    def _get_document_instance(self, document_id, operation):
        instance = request.env["gov.document.instance"].browse(document_id)
        instance.check_access_rights(operation)
        instance.check_access_rule(operation)
        instance = instance.exists()
        if not instance:
            return None
        return instance

    @http.route("/gov/document/load", type="jsonrpc", auth="user")
    def load_document(self, document_id):
        """Retorna payload completo para o builder."""
        instance = self._get_document_instance(document_id, "read")
        if not instance:
            return {"error": f"Documento não encontrado: {document_id}"}
        return {
            "id": instance.id,
            "name": instance.name,
            "state": instance.state,
            "document_type": {
                "code": instance.document_type_id.code,
                "name": instance.document_type_id.name,
            },
            "layout_json": instance.layout_json or "[]",
            "resolved_context": json.loads(instance.resolved_context_json or "{}"),
            "version": instance.current_version_no,
        }

    @http.route("/gov/document/save_layout", type="jsonrpc", auth="user")
    def save_layout(self, document_id, layout_json):
        """Persiste o layout_json e regenera o Typst."""
        instance = self._get_document_instance(document_id, "write")
        if not instance:
            return {"error": f"Documento não encontrado: {document_id}"}
        nodes = json.loads(layout_json)
        instance.set_layout(nodes)
        typst = request.env["gov.document.typst.renderer"].render_instance(instance)
        instance.write({"typst_source": typst})
        return {"success": True, "typst_source": typst}

    @http.route("/gov/document/resolve_context", type="jsonrpc", auth="user")
    def resolve_context(self, document_id):
        """Resolve e retorna o contexto completo do documento."""
        instance = self._get_document_instance(document_id, "read")
        if not instance:
            return {"error": f"Documento não encontrado: {document_id}"}
        ctx = request.env["gov.document.context.resolver"].resolve_instance_context(instance)
        instance.resolved_context_json = json.dumps(ctx)
        return ctx

    @http.route("/gov/document/render_typst", type="jsonrpc", auth="user")
    def render_typst(self, document_id):
        """Renderiza e retorna o Typst atualizado."""
        instance = self._get_document_instance(document_id, "read")
        if not instance:
            return {"error": f"Documento não encontrado: {document_id}"}
        typst = request.env["gov.document.typst.renderer"].render_instance(instance)
        return {"typst_source": typst}

    @http.route("/gov/document/block_catalog", type="jsonrpc", auth="user")
    def get_block_catalog(self, document_type_code=None):
        """Retorna catálogo de blocos disponíveis, opcionalmente filtrado por tipo."""
        domain = [("active", "=", True)]
        if document_type_code:
            doc_type = request.env["gov.document.type"].search(
                [("code", "=", document_type_code)],
                limit=1,
            )
            if doc_type:
                domain += [
                    "|",
                    ("allowed_document_type_ids", "=", False),
                    ("allowed_document_type_ids", "in", doc_type.ids),
                ]
        blocks = request.env["gov.document.block.catalog"].search(domain, order="sequence, name")
        return [
            {
                "id": block.id,
                "code": block.code,
                "name": block.name,
                "block_kind": block.block_kind,
                "category": block.category,
                "icon": block.icon,
                "description": block.description,
                "default_props": block.get_default_props(),
                "supports_binding": block.supports_binding,
                "is_locked_by_default": block.is_locked_by_default,
                "typst_renderer_key": block.typst_renderer_key,
            }
            for block in blocks
        ]

    @http.route("/gov/document/create_from_template", type="jsonrpc", auth="user")
    def create_from_template(self, document_type_code, process_id=None):
        """Cria nova instância a partir do template padrão do tipo documental."""
        doc_type = request.env["gov.document.type"].search(
            [("code", "=", document_type_code)],
            limit=1,
        )
        if not doc_type:
            return {"error": f"Tipo documental não encontrado: {document_type_code}"}
        template = request.env["gov.document.template"].search(
            [("document_type_id", "=", doc_type.id), ("active", "=", True)],
            limit=1,
        )
        vals = {
            "name": f"{doc_type.name} — Rascunho",
            "document_type_id": doc_type.id,
            "template_id": template.id if template else False,
            "layout_json": template.layout_schema_json if template else "[]",
        }
        if process_id not in (None, False, ""):
            vals["process_id"] = int(process_id)
        instance = request.env["gov.document.instance"].create(vals)
        return {"document_id": instance.id}
