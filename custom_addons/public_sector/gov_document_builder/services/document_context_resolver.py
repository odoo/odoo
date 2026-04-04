import json
import logging
from datetime import timedelta
from numbers import Number

from odoo import fields, models

_logger = logging.getLogger(__name__)


class GovDocumentContextResolver(models.AbstractModel):
    """Resolve contexto declarativo e valores de binding para documentos."""

    _name = "gov.document.context.resolver"
    _description = "Resolvedor de Contexto de Documento"

    def resolve_instance_context(self, instance):
        """Retorna o contexto completo usado pelo builder e pelo renderer."""
        process = instance.process_id
        context = {
            "process": self._resolve_process_namespace(process),
            "legal": self._resolve_legal_namespace(process),
            "procurement": self._resolve_procurement_namespace(process),
            "auction": self._resolve_auction_namespace(process),
            "contract": self._resolve_contract_namespace(process),
            "budget": self._resolve_budget_namespace(process),
            "execution": self._resolve_execution_namespace(process),
        }
        if context["process"]:
            context["process"].setdefault("modalidade", context["legal"].get("modalidade", ""))
        context["reconciliation"] = self.compute_reconciliation_namespace(context)
        context["document"] = self._resolve_document(instance)
        context["institution"] = self._resolve_institution(instance)
        return context

    def resolve_block_value(self, instance, block_node):
        """Resolve o valor de um nó específico, considerando binding e transformers."""
        binding = block_node.get("binding", {})
        if not binding:
            return block_node.get("props", {})
        context = self.resolve_instance_context(instance)
        return self.resolve_binding(binding, context)

    def resolve_binding(self, binding, context):
        """
        Resolve um binding declarativo contra o contexto.
        binding: {'source': 'process', 'path': 'subject', 'fallback': '', 'transform': 'strip'}
        """
        source = binding.get("source", "")
        path = binding.get("path", "")
        fallback = binding.get("fallback", "")
        transform = binding.get("transform", "")
        try:
            value = context.get(source, {})
            if path == "*":
                return self.apply_transformer(value, transform)
            for key in path.split("."):
                if not key:
                    continue
                value = value.get(key, fallback) if isinstance(value, dict) else fallback
            if value is None:
                value = fallback
            return self.apply_transformer(value, transform)
        except Exception:
            return fallback

    def evaluate_visibility_rule(self, rule, context):
        """Avalia uma regra declarativa de visibilidade contra o contexto resolvido."""
        if not rule:
            return True
        try:
            parts = (rule or "").strip().split()
            if len(parts) < 2:
                raise ValueError("Regra incompleta")

            path = parts[0]
            operator = parts[1]
            literal = " ".join(parts[2:]) if len(parts) > 2 else None
            if "." not in path:
                raise ValueError("Path de binding inválida")

            source, binding_path = path.split(".", 1)
            value = self.resolve_binding(
                {
                    "source": source,
                    "path": binding_path,
                    "fallback": None,
                },
                context,
            )

            if operator == "exists":
                return self._visibility_value_exists(value)
            if operator == "not_exists":
                return not self._visibility_value_exists(value)

            if literal is None:
                raise ValueError("Literal ausente para comparação")

            literal = self._normalize_visibility_literal(literal)
            if operator in {">", "<"}:
                left = self._coerce_float(value)
                right = self._coerce_float(literal)
                if left is None or right is None:
                    raise ValueError("Comparação numérica inválida")
                return left > right if operator == ">" else left < right
            if operator == "==":
                return str(value or "") == literal
            if operator == "!=":
                return str(value or "") != literal

            raise ValueError(f"Operador não suportado: {operator}")
        except Exception as error:
            _logger.warning(
                "gov_document_builder: falha ao avaliar visibility_rule=%s: %s",
                rule,
                error,
            )
            return True

    def apply_transformer(self, value, transform):
        """Aplica transformações declarativas do binding."""
        if not transform:
            return value
        if transform == "date_br":
            if hasattr(value, "strftime"):
                return value.strftime("%d/%m/%Y")
            if isinstance(value, str) and value:
                try:
                    parsed_date = fields.Date.to_date(value)
                except Exception:
                    parsed_date = None
                if parsed_date:
                    return parsed_date.strftime("%d/%m/%Y")
            return value
        if transform == "currency_br":
            numeric_value = self._coerce_float(value)
            if numeric_value is not None:
                formatted = f"{numeric_value:,.2f}"
                return formatted.replace(",", "_").replace(".", ",").replace("_", ".")
            return value
        if transform == "percentual":
            numeric_value = self._coerce_float(value)
            if numeric_value is not None:
                formatted = f"{numeric_value * 100:,.2f}%"
                return formatted.replace(",", "_").replace(".", ",").replace("_", ".")
            return value
        if transform == "lista_br":
            if isinstance(value, (list, tuple, set)):
                items = [str(item) for item in value if item not in (None, "")]
                if not items:
                    return ""
                if len(items) == 1:
                    return items[0]
                if len(items) == 2:
                    return f"{items[0]} e {items[1]}"
                return f"{', '.join(items[:-1])} e {items[-1]}"
            return value
        if not isinstance(value, str):
            return value
        transformers = {
            "strip": lambda current: current.strip(),
            "upper": lambda current: current.upper(),
            "lower": lambda current: current.lower(),
            "title": lambda current: current.title(),
        }
        return transformers.get(transform, lambda current: current)(value)

    def _resolve_document(self, instance):
        return {
            "name": instance.name,
            "type_code": instance.document_type_id.code,
            "version": instance.current_version_no,
            "date": fields.Date.today().strftime("%d/%m/%Y"),
        }

    def _resolve_process_namespace(self, process):
        if not process:
            return {}
        process_name = process.name or ""
        process_subject = process.subject or ""
        return {
            "name": process_name,
            "number": process_name,
            "subject": process_subject,
            "objeto": process_subject,
            "ug_id": {
                "name": process.ug_id.name or "",
            },
            "ug_id_name": process.ug_id.name or "",
            "responsible_id": {
                "name": process.responsible_id.name or "",
            },
            "responsible_name": process.responsible_id.name or "",
            "state": process.state or "",
            "process_scope": process.process_scope or "",
            "valor_total_estimado": process.valor_total_estimado or 0.0,
            "valor_estimado": process.valor_total_estimado or 0.0,
        }

    def _resolve_legal_namespace(self, process):
        legal = {
            "base_legal": [],
            "modalidade": "",
            "hipotese_dispensa": "",
        }
        if not process:
            return legal

        parameters = self._get_process_parameters(
            process,
            phase_names=("instrucao", "planejamento"),
            section="required_by_law",
        )
        legal["base_legal"] = [param.name for param in parameters if param.name]
        legal["modalidade"] = self._get_parameter_value(process, "modalidade", parameters=parameters) or ""
        legal["hipotese_dispensa"] = (
            self._get_parameter_value(process, "hipotese_dispensa", parameters=parameters) or ""
        )
        return legal

    def _resolve_procurement_namespace(self, process):
        procurement = {
            "valor_estimado_total": 0.0,
            "preco_unitario_referencia": 0.0,
            "quantidade_estimada_total": 0.0,
            "data_pesquisa_preco": "",
        }
        if not process:
            return procurement

        items = process.planilha_item_ids
        if items:
            first_item = items[0]
            procurement["valor_estimado_total"] = sum(items.mapped("annual_total"))
            procurement["preco_unitario_referencia"] = first_item.unit_price or 0.0
            procurement["quantidade_estimada_total"] = sum(
                item.annual_quantity or ((item.monthly_quantity or 0.0) * 12.0)
                for item in items
            )
        procurement["data_pesquisa_preco"] = (
            self._get_parameter_value(process, "data_pesquisa_preco") or ""
        )
        return procurement

    def _resolve_auction_namespace(self, process):
        auction = {
            "valor_arrematado": 0.0,
            "preco_unitario_final": 0.0,
            "fornecedor": "",
            "desconto_percentual": 0.0,
            "data_homologacao": "",
        }
        licitacao = self._get_linked_record(process, "gov.licitacao")
        if not licitacao:
            return auction

        auction["valor_arrematado"] = self._read_number(licitacao, "valor_arrematado")
        auction["preco_unitario_final"] = self._read_number(licitacao, "preco_unitario_final")
        auction["fornecedor"] = self._read_related_name(licitacao, "fornecedor_id")
        auction["data_homologacao"] = self._read_scalar(licitacao, "data_homologacao", "")
        if "desconto_percentual" in licitacao._fields:
            auction["desconto_percentual"] = self._read_number(licitacao, "desconto_percentual")
        else:
            procurement_total = (
                self._coerce_float(
                    self._resolve_procurement_namespace(process)["valor_estimado_total"]
                )
                or 0.0
            )
            if procurement_total > 0 and auction["valor_arrematado"] > 0:
                auction["desconto_percentual"] = max(
                    (procurement_total - auction["valor_arrematado"]) / procurement_total,
                    0.0,
                )
        return auction

    def _resolve_contract_namespace(self, process):
        contract = {
            "valor_contratado": 0.0,
            "numero_contrato": "",
            "data_inicio_vigencia": "",
            "data_fim_vigencia": "",
            "quantidade_aditivos": 0,
            "saldo_restante": 0.0,
        }
        contrato = self._get_linked_record(process, "gov.contrato")
        if not contrato:
            return contract

        contract["valor_contratado"] = self._read_number(contrato, "valor_contratado")
        contract["numero_contrato"] = self._read_scalar(contrato, "numero_contrato", "")
        contract["data_inicio_vigencia"] = self._read_scalar(contrato, "data_inicio_vigencia", "")
        contract["data_fim_vigencia"] = self._read_scalar(contrato, "data_fim_vigencia", "")
        if "quantidade_aditivos" in contrato._fields:
            contract["quantidade_aditivos"] = int(self._read_number(contrato, "quantidade_aditivos"))
        elif "aditivo_ids" in contrato._fields:
            contract["quantidade_aditivos"] = len(contrato.aditivo_ids)
        contract["saldo_restante"] = self._read_number(contrato, "saldo_restante")
        return contract

    def _resolve_budget_namespace(self, process):
        budget = {
            "valor_empenhado": 0.0,
            "saldo_disponivel": 0.0,
            "exercicio": 0,
            "natureza_despesa": [],
            "fonte_recurso": [],
        }
        if not process:
            return budget

        dotacoes = process.dotacao_ids
        if not dotacoes:
            return budget

        budget["valor_empenhado"] = sum(
            dotacao.valor_estimado or 0.0 for dotacao in dotacoes if dotacao.reservado
        )
        budget["saldo_disponivel"] = sum(dotacoes.mapped("saldo_disponivel"))
        budget["exercicio"] = dotacoes[0].exercicio or 0
        budget["natureza_despesa"] = self._deduplicate(
            dotacoes.mapped("natureza_despesa")
        )
        budget["fonte_recurso"] = self._deduplicate(dotacoes.mapped("fonte_recurso"))
        return budget

    def _resolve_execution_namespace(self, process):
        execution = {
            "valor_empenhado_acumulado": 0.0,
            "valor_liquidado_acumulado": 0.0,
            "ordens_fornecimento_count": 0,
            "quantidade_entregue": 0.0,
            "status_aceite_fiscal": "",
        }
        empenhos = self._get_linked_records(process, "gov.empenho")
        if not empenhos:
            return execution

        active_empenhos = empenhos.filtered(lambda rec: rec.state != "anulado")
        if "valor_liquido" in active_empenhos._fields:
            execution["valor_empenhado_acumulado"] = sum(active_empenhos.mapped("valor_liquido"))
        else:
            execution["valor_empenhado_acumulado"] = sum(active_empenhos.mapped("valor_empenho"))

        if "ordens_fornecimento_count" in active_empenhos._fields:
            execution["ordens_fornecimento_count"] = int(
                sum(active_empenhos.mapped("ordens_fornecimento_count"))
            )
        elif "ordem_fornecimento_ids" in active_empenhos._fields:
            execution["ordens_fornecimento_count"] = sum(
                len(empenho.ordem_fornecimento_ids) for empenho in active_empenhos
            )

        if "quantidade_entregue" in active_empenhos._fields:
            execution["quantidade_entregue"] = sum(active_empenhos.mapped("quantidade_entregue"))

        if "status_aceite_fiscal" in active_empenhos._fields:
            statuses = self._deduplicate(active_empenhos.mapped("status_aceite_fiscal"))
            execution["status_aceite_fiscal"] = ", ".join(statuses)

        liquidacao_model = self.env.get("gov.liquidacao")
        if liquidacao_model is not None:
            liquidacoes = liquidacao_model.search(
                [
                    ("empenho_id", "in", active_empenhos.ids),
                    ("state", "in", ("atestado", "liquidado")),
                ]
            )
            execution["valor_liquidado_acumulado"] = sum(liquidacoes.mapped("valor_liquidado"))

        return execution

    def _resolve_reconciliation_namespace(self, context):
        budget = context.get("budget", {})
        procurement = context.get("procurement", {})
        auction = context.get("auction", {})
        contract = context.get("contract", {})
        execution = context.get("execution", {})

        valor_empenhado = self._coerce_float(budget.get("valor_empenhado")) or 0.0
        valor_liquidado = self._coerce_float(execution.get("valor_liquidado_acumulado")) or 0.0
        valor_estimado_total = self._coerce_float(procurement.get("valor_estimado_total")) or 0.0
        valor_arrematado = self._coerce_float(auction.get("valor_arrematado")) or 0.0
        valor_contratado = self._coerce_float(contract.get("valor_contratado")) or 0.0

        superavit = 0.0
        deficit = 0.0
        if valor_estimado_total > 0 and valor_arrematado > 0:
            if valor_arrematado < valor_estimado_total:
                superavit = valor_estimado_total - valor_arrematado
            elif valor_arrematado > valor_estimado_total:
                deficit = valor_arrematado - valor_estimado_total

        valor_a_conciliar = max(valor_empenhado - valor_liquidado, 0.0)
        situacao = "regular"
        if valor_contratado and valor_empenhado > valor_contratado:
            situacao = "com_devolucao"
        elif valor_a_conciliar > 0:
            situacao = "pendente"

        prazo_conciliacao = ""
        data_fim_vigencia = contract.get("data_fim_vigencia")
        if data_fim_vigencia:
            end_date = fields.Date.to_date(data_fim_vigencia)
            if end_date:
                prazo_conciliacao = fields.Date.to_string(end_date + timedelta(days=30))

        return {
            "valor_a_conciliar": valor_a_conciliar,
            "superavit": superavit,
            "deficit": deficit,
            "situacao_conciliacao": situacao,
            "prazo_conciliacao": prazo_conciliacao,
        }

    def compute_reconciliation_namespace(self, context):
        """Recalcula o namespace de conciliação a partir de um contexto já montado."""
        return self._resolve_reconciliation_namespace(context)

    def _normalize_visibility_literal(self, literal):
        cleaned = (literal or "").strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
            cleaned = cleaned[1:-1]
        return cleaned

    def _visibility_value_exists(self, value):
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, dict, set)):
            return bool(value)
        return True

    def _resolve_institution(self, instance):
        company = getattr(instance, "company_id", False) or self.env.company
        return {
            "name": company.name,
            "city": company.city or "",
            "state": company.state_id.name if company.state_id else "",
        }

    def _get_process_parameters(self, process, phase_names=(), section=None):
        if not process:
            return self.env["gov.processo.parametro"]

        parameters = process.parameter_ids
        if phase_names:
            phase_map = getattr(process, "_FASE_MAP", {})
            allowed_phases = {
                phase_map[phase_name]
                for phase_name in phase_names
                if phase_name in phase_map
            }
            parameters = parameters.filtered(lambda rec: rec.fase in allowed_phases)
        if section:
            parameters = parameters.filtered(lambda rec: rec.section == section)
        return parameters

    def _get_parameter_value(self, process, key, parameters=None):
        if not process:
            return ""
        parameter_records = parameters if parameters is not None else process.parameter_ids
        parameter = parameter_records.filtered(lambda rec: rec.key == key)[:1]
        if not parameter:
            parameter = process.parameter_ids.filtered(lambda rec: rec.key == key)[:1]
        if not parameter:
            return ""
        return self._parse_parameter_value(parameter)

    def _parse_parameter_value(self, parameter):
        raw_value = (parameter.value_text or "").strip()
        if not raw_value:
            return ""
        if parameter.value_type in {"json", "array", "object"}:
            try:
                return json.loads(raw_value)
            except json.JSONDecodeError:
                return raw_value
        if parameter.value_type in {"number", "monetary"}:
            numeric_value = self._coerce_float(raw_value)
            return numeric_value if numeric_value is not None else raw_value
        if parameter.value_type == "boolean":
            return raw_value.lower() in {"1", "true", "sim", "s", "yes"}
        return raw_value

    def _get_linked_record(self, process, model_name):
        records = self._get_linked_records(process, model_name)
        return records[:1]

    def _get_linked_records(self, process, model_name):
        if not process:
            model = self.env.get(model_name)
            return model.browse() if model is not None else self.env["ir.model"].browse()

        model = self.env.get(model_name)
        if model is None:
            return self.env["ir.model"].browse()

        record_ids = process.vinculo_ids.filtered(
            lambda rec: rec.model_name == model_name
        ).mapped("record_id")
        if not record_ids:
            return model.browse()
        return model.browse(record_ids).exists()

    def _read_scalar(self, record, field_name, default=""):
        if not record or field_name not in record._fields:
            return default
        value = record[field_name]
        if value in (None, False):
            return default
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value

    def _read_number(self, record, field_name):
        if not record or field_name not in record._fields:
            return 0.0
        return self._coerce_float(record[field_name]) or 0.0

    def _read_related_name(self, record, field_name):
        if not record or field_name not in record._fields:
            return ""
        related_record = record[field_name]
        return related_record.name or related_record.display_name or ""

    def _coerce_float(self, value):
        if isinstance(value, Number):
            return float(value)
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            if "," in normalized and "." in normalized:
                normalized = normalized.replace(".", "").replace(",", ".")
            elif "," in normalized:
                normalized = normalized.replace(",", ".")
            try:
                return float(normalized)
            except ValueError:
                return None
        return None

    def _deduplicate(self, values):
        result = []
        seen = set()
        for value in values:
            if value in (None, "", False) or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result
