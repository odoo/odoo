from odoo import fields, models


class GovDocumentContextResolver(models.AbstractModel):
    """Resolve contexto declarativo e valores de binding para documentos."""

    _name = "gov.document.context.resolver"
    _description = "Resolvedor de Contexto de Documento"

    def resolve_instance_context(self, instance):
        """
        Retorna dict com todos os dados resolvidos para o documento.
        Inclui: dados do processo, metadados institucionais, assinantes, data.
        """
        ctx = {}
        ctx["document"] = {
            "name": instance.name,
            "type_code": instance.document_type_id.code,
            "version": instance.current_version_no,
            "date": fields.Date.today().strftime("%d/%m/%Y"),
        }
        if instance.process_id:
            ctx["process"] = self._resolve_process(instance.process_id)
        ctx["institution"] = self._resolve_institution(instance)
        return ctx

    def resolve_block_value(self, instance, block_node):
        """
        Resolve o valor de um no especifico, considerando binding e transformers.
        block_node: dict com keys type, props, binding.
        """
        binding = block_node.get("binding", {})
        if not binding:
            return block_node.get("props", {})
        ctx = self.resolve_instance_context(instance)
        return self.resolve_binding(binding, ctx)

    def resolve_binding(self, binding, context):
        """
        Resolve um binding declarativo contra o contexto.
        binding: {'source': 'process', 'path': 'objeto', 'fallback': '', 'transform': 'strip'}
        """
        source = binding.get("source", "")
        path = binding.get("path", "")
        fallback = binding.get("fallback", "")
        transform = binding.get("transform", "")
        try:
            value = context.get(source, {})
            for key in path.split("."):
                if key:
                    value = value.get(key, fallback) if isinstance(value, dict) else fallback
            return self.apply_transformer(value, transform)
        except Exception:
            return fallback

    def apply_transformer(self, value, transform):
        """Aplica transformacoes: strip, upper, lower, date_br, currency_br."""
        if not transform:
            return value
        if transform == "date_br":
            if hasattr(value, "strftime"):
                return value.strftime("%d/%m/%Y")
            return value
        if transform == "currency_br":
            if isinstance(value, (int, float)):
                formatted = f"{value:,.2f}"
                return formatted.replace(",", "_").replace(".", ",").replace("_", ".")
            return value
        if not isinstance(value, str):
            return value
        transformers = {
            "strip": lambda v: v.strip(),
            "upper": lambda v: v.upper(),
            "lower": lambda v: v.lower(),
            "title": lambda v: v.title(),
        }
        return transformers.get(transform, lambda v: v)(value)

    def _resolve_process(self, process):
        """
        Extrai campos do processo licitatorio em dict plano.
        Adaptar campos conforme modelo gov.procurement.process real.
        """
        result = {}
        safe_fields = ["name", "number", "objeto", "modalidade", "valor_estimado"]
        for field_name in safe_fields:
            if hasattr(process, field_name):
                value = getattr(process, field_name)
                result[field_name] = str(value) if value else ""
        return result

    def _resolve_institution(self, instance):
        company = instance.company_id if hasattr(instance, "company_id") else self.env.company
        return {
            "name": company.name,
            "city": company.city or "",
            "state": company.state_id.name if company.state_id else "",
        }
