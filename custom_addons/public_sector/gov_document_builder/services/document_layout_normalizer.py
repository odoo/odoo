import json
import uuid

from odoo import models


class GovDocumentLayoutNormalizer(models.AbstractModel):
    """Valida e normaliza layouts JSON antes da compilação do documento."""

    _name = "gov.document.layout.normalizer"
    _description = "Normalizador de Layout de Documento"

    def normalize(self, layout_json_str):
        """
        Recebe string JSON do layout e retorna lista de nós normalizados.
        Garante que cada nó tenha: id, type, sequence, props, binding.
        """
        try:
            nodes = json.loads(layout_json_str or "[]")
        except (ValueError, TypeError):
            return []
        normalized = []
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            normalized.append(
                {
                    "id": node.get("id") or str(uuid.uuid4())[:8],
                    "type": node.get("type", "rich_text"),
                    "sequence": node.get("sequence", (i + 1) * 10),
                    "props": node.get("props", {}),
                    "binding": node.get("binding", {}),
                    "children": node.get("children", []),
                    "locked": node.get("locked", False),
                }
            )
        normalized.sort(key=lambda n: n["sequence"])
        return normalized

    def validate(self, nodes):
        """
        Valida lista de nós normalizados.
        Retorna lista de erros: [{'node_id': ..., 'message': ...}]
        """
        errors = []
        ids_seen = set()
        for node in nodes:
            if node["id"] in ids_seen:
                errors.append({"node_id": node["id"], "message": "ID duplicado."})
            ids_seen.add(node["id"])
            if not node.get("type"):
                errors.append({"node_id": node["id"], "message": "Campo type ausente."})
        return errors
