import hashlib
import io
import json
from collections import OrderedDict

from odoo import fields, models
from odoo.exceptions import UserError


class GovXlsxWorkerService(models.AbstractModel):
    _name = "gov.xlsx.worker.service"
    _description = "Servico de Geracao XLSX GOV"

    _ITEM_DATASET_KEYS = (
        "xlsx_item_rows_json",
        "planilha_item_rows_json",
        "itens_planilha_json",
        "quantitativos_item_rows_json",
    )
    _LOT_DATASET_KEYS = (
        "xlsx_lot_rows_json",
        "planilha_lotes_json",
        "lotes_resumo_json",
        "estimativa_lotes_json",
    )
    _SCHEDULE_DATASET_KEYS = (
        "xlsx_schedule_rows_json",
        "planilha_cronograma_json",
        "cronograma_pedidos_json",
    )
    _MONTHS = [
        ("jan", "Jan"),
        ("fev", "Fev"),
        ("mar", "Mar"),
        ("abr", "Abr"),
        ("mai", "Mai"),
        ("jun", "Jun"),
        ("jul", "Jul"),
        ("ago", "Ago"),
        ("set", "Set"),
        ("out", "Out"),
        ("nov", "Nov"),
        ("dez", "Dez"),
    ]

    def _default_profile_for_scope(self, scope):
        return "service_continuous_labor" if scope == "servicos_continuados" else "procurement_reference"

    def generate_workbook(self, processo, doc=None, profile=None):
        selected_profile = (
            profile
            or getattr(doc, "xlsx_profile", False)
            or getattr(processo, "xlsx_profile", False)
            or self._default_profile_for_scope(processo.process_scope)
        )
        if selected_profile == "service_continuous_labor":
            return self.generate_service_continuous_workbook(processo, doc=doc)
        return self.generate_procurement_workbook(processo, doc=doc)

    def generate_procurement_workbook(self, processo, doc=None):
        payload = self.build_procurement_payload(processo, doc=doc)
        workbook_binary = self._render_procurement_workbook(payload)
        filename = self._build_filename(processo, doc, profile="procurement_reference")
        return {
            "payload": payload,
            "binary": workbook_binary,
            "filename": filename,
            "sha256": hashlib.sha256(workbook_binary).hexdigest(),
            "row_count": len(payload["items"]),
            "lot_count": len(payload["lots"]),
        }

    def generate_service_continuous_workbook(self, processo, doc=None):
        payload = self.build_service_continuous_payload(processo, doc=doc)
        workbook_binary = self._render_service_continuous_workbook(payload)
        filename = self._build_filename(processo, doc, profile="service_continuous_labor")
        return {
            "payload": payload,
            "binary": workbook_binary,
            "filename": filename,
            "sha256": hashlib.sha256(workbook_binary).hexdigest(),
            "row_count": len(payload["items"]),
            "lot_count": len(payload["lots"]),
        }

    def build_procurement_payload(self, processo, doc=None):
        parameter_values = self._get_parameter_values(processo)

        items = self._load_dataset(parameter_values, self._ITEM_DATASET_KEYS)
        lots = self._load_dataset(parameter_values, self._LOT_DATASET_KEYS)
        schedule = self._load_dataset(parameter_values, self._SCHEDULE_DATASET_KEYS)
        if not items and hasattr(processo, "planilha_item_ids") and processo.planilha_item_ids:
            items = processo._serialize_planilha_item_rows()
        if not lots and hasattr(processo, "planilha_item_ids") and processo.planilha_item_ids:
            lots = processo._serialize_planilha_lot_rows()
        if not schedule and hasattr(processo, "planilha_item_ids") and processo.planilha_item_ids:
            schedule = processo._serialize_planilha_schedule_rows()

        items = self._normalize_items(items or [])
        explicit_lots = self._normalize_lots(lots or [])
        if not items and explicit_lots:
            items = self._build_synthetic_items_from_lots(explicit_lots)
        if not items:
            raise UserError(
                (
                    "Nao ha dados estruturados suficientes para gerar a planilha XLSX. "
                    "Preencha a variavel xlsx_item_rows_json (ou equivalente) no processo."
                )
            )

        lots = self._merge_lots(items, explicit_lots)
        schedule = self._normalize_schedule(schedule, lots)
        metadata = self._build_workbook_metadata(
            processo,
            doc,
            parameter_values,
            items,
            lots,
        )

        return {
            "metadata": metadata,
            "items": items,
            "lots": lots,
            "schedule": schedule,
        }

    def build_service_continuous_payload(self, processo, doc=None):
        payload = self.build_procurement_payload(processo, doc=doc)
        parameter_values = self._get_parameter_values(processo)
        payload["metadata"] = self._build_service_workbook_metadata(
            processo,
            doc,
            parameter_values,
            payload["items"],
            payload["lots"],
        )
        return payload

    def _build_filename(self, processo, doc=None, profile="procurement_reference"):
        if profile == "service_continuous_labor":
            doc_type = "servicos_continuados"
        else:
            doc_type = (doc.doc_type if doc else "processo") or "processo"
        process_number = (processo.name or "processo").replace("/", "-").replace(" ", "_")
        return f"{doc_type}_{process_number}_planilha.xlsx"

    def _get_parameter_values(self, processo):
        values = {}
        for parameter in processo.parameter_ids:
            values[parameter.key] = parameter.value_text or ""
        return values

    def _parameter_first(self, parameter_values, *keys, default=""):
        for key in keys:
            value = (parameter_values.get(key) or "").strip()
            if value:
                return value
        return default

    def _company_location_label(self, processo):
        company = processo.ug_id or self.env.company
        partner = company.partner_id
        city = (partner.city or "").strip()
        state = (partner.state_id.code or partner.state_id.name or "").strip()
        if city and state:
            return f"{city}/{state}"
        return city or state or ""

    def _format_currency_brl(self, value):
        amount = float(value or 0.0)
        formatted = f"{amount:,.2f}"
        formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
        return f"R$ {formatted}"

    def _build_workbook_metadata(self, processo, doc, parameter_values, items, lots):
        total_value = sum(lot.get("expected_value") or 0.0 for lot in lots)
        if not total_value:
            total_value = (
                processo.valor_total_estimado
                or sum((item.get("annual_quantity") or 0.0) * (item.get("unit_price") or 0.0) for item in items)
            )

        location = self._company_location_label(processo)
        reference_number = self._parameter_first(
            parameter_values,
            "tr_numero",
            "etp_numero",
            "dfd_referencia_tr",
            "identificacao_processo",
            "processo_numero_tr",
            "processo_numero_externo",
            default=processo.name or "",
        )
        orgao_nome = self._parameter_first(
            parameter_values,
            "orgao_nome",
            "orgao_emitente_tr",
            default=(processo.ug_id.name or self.env.company.name or ""),
        )
        unidade_nome = self._parameter_first(
            parameter_values,
            "unidade_nome",
            "unidade_emitente_tr",
            "unidade_requisitante_extenso",
            default=orgao_nome,
        )
        objeto_titulo = self._parameter_first(
            parameter_values,
            "objeto_titulo",
            "objeto_tr_resumo",
            "objeto_etp",
            default=processo.subject or (doc.name if doc else ""),
        )
        modalidade = self._parameter_first(
            parameter_values,
            "modalidade_planejada",
            "modalidade_selecao",
            default="Pregao Eletronico - Sistema de Registro de Precos",
        )
        criterio = self._parameter_first(
            parameter_values,
            "criterio_julgamento",
            "configuracao_licitatoria_texto",
            default="Menor preco por lote (Art. 33, I - Lei 14.133/2021)",
        )
        vigencia = self._parameter_first(
            parameter_values,
            "vigencia_arp_texto_tr",
            "vigencia_arp_edital",
            default="12 meses, prorrogavel (Art. 84, par. 1 - Lei 14.133/2021)",
        )
        entrega = self._parameter_first(
            parameter_values,
            "forma_fornecimento_texto",
            "recebimento_texto",
            default="CIF no destino final, com frete incluso.",
        )
        valor_total_display = self._parameter_first(
            parameter_values,
            "valor_estimado_extenso",
            "valor_estimado_global_tr",
            "valor_estimado_global_etp",
            default=self._format_currency_brl(total_value),
        )
        elaborated_by = self._parameter_first(
            parameter_values,
            "unidade_emitente_tr",
            "unidade_nome",
            "unidade_requisitante_extenso",
            default=unidade_nome or orgao_nome,
        )
        anvisa_note = self._parameter_first(
            parameter_values,
            "anvisa_note",
            default=(
                "Obrigatorio para itens sujeitos a registro ou notificacao sanitaria."
                if any("ANVISA" in (item.get("specification") or "").upper() or item.get("class_abc") in ("A", "B") for item in items)
                else "Aplicavel conforme a natureza do item."
            ),
        )
        legal_basis = self._parameter_first(
            parameter_values,
            "base_legal_planilha",
            default="Lei n.o 14.133/2021 e Decreto n.o 11.462/2023 (SRP)",
        )
        exercise_text = self._parameter_first(
            parameter_values,
            "exercicio_tr",
            "exercicio_documento",
            default=str(fields.Date.today().year),
        )
        schedule_cycle = exercise_text
        if exercise_text.isdigit():
            schedule_cycle = f"{exercise_text}/{int(exercise_text) + 1}"

        header_orgao = orgao_nome.upper() if orgao_nome else "PROCESSO ADMINISTRATIVO"
        if unidade_nome and unidade_nome != orgao_nome:
            header_orgao = f"{header_orgao} - {unidade_nome.upper()}"
        reference_line = f"{reference_number} - {modalidade}"
        subject_line = f"{objeto_titulo} - Lei n.o 14.133/2021"
        if location:
            subject_line = f"{subject_line} - {location}"

        return {
            "processo_numero": processo.name or "",
            "processo_assunto": processo.subject or "",
            "process_scope": processo.process_scope or "",
            "process_type": processo.process_type or "",
            "doc_nome": doc.name if doc else "",
            "doc_tipo": doc.doc_type if doc else "",
            "documento_referencia": doc.ai_template_id.name if doc and doc.ai_template_id else "",
            "valor_total_estimado": total_value,
            "orgao_nome": orgao_nome,
            "unidade_nome": unidade_nome,
            "objeto_titulo": objeto_titulo,
            "referencia_numero": reference_number,
            "modalidade": modalidade,
            "criterio_julgamento": criterio,
            "vigencia_arp": vigencia,
            "entrega": entrega,
            "valor_total_display": valor_total_display,
            "anvisa_note": anvisa_note,
            "base_legal": legal_basis,
            "elaborated_by": elaborated_by,
            "total_lotes": len(lots),
            "total_itens": len(items),
            "header_orgao": header_orgao,
            "header_reference_line": reference_line,
            "header_subject_line": subject_line,
            "legend_line": (
                "Classe A (azul) = itens criticos de alto giro | "
                "Classe B (vermelho) = itens intermediarios | "
                "Classe C (cinza) = utensilios gerais"
            ),
            "summary_title": f"RESUMO POR LOTE - {reference_number}",
            "summary_subtitle": (
                f"{objeto_titulo} - {unidade_nome or location or processo.subject or ''}"
            ),
            "schedule_title": (
                f"CRONOGRAMA ORIENTATIVO DE ORDENS DE FORNECIMENTO - ARP {schedule_cycle}"
            ),
            "schedule_subtitle": (
                "Calibrado ao ciclo hidrologico do Rio Madeira "
                "(cheia: jan-jun | seca: jul-out | transicao: nov-dez)"
            ),
        }

    def _build_service_workbook_metadata(self, processo, doc, parameter_values, items, lots):
        metadata = self._build_workbook_metadata(processo, doc, parameter_values, items, lots)
        exercise_text = self._parameter_first(
            parameter_values,
            "exercicio_tr",
            "exercicio_documento",
            default=str(fields.Date.today().year),
        )
        cycle = exercise_text
        if exercise_text.isdigit():
            cycle = f"{exercise_text}/{int(exercise_text) + 1}"
        metadata.update(
            {
                "header_reference_line": (
                    f"{metadata['referencia_numero']} - {metadata['modalidade']} - "
                    "Servicos Continuados"
                ),
                "legend_line": (
                    "Qtd. Postos = postos ativos por mes | "
                    "Custo mensal = postos x valor unitario | "
                    "Cobertura mensal = ferias, reserva tecnica e medicao"
                ),
                "summary_title": f"RESUMO DE POSTOS E CUSTOS - {metadata['referencia_numero']}",
                "summary_subtitle": (
                    f"{metadata['objeto_titulo']} - dedicacao continuada de mao de obra"
                ),
                "schedule_title": f"CRONOGRAMA DE COBERTURA E MEDICAO - {cycle}",
                "schedule_subtitle": (
                    "Use esta aba para distribuir cobertura mensal, medicao, ferias, "
                    "substituicoes e janelas de fiscalizacao."
                ),
                "regime_execucao": self._parameter_first(
                    parameter_values,
                    "instrumento_contratual_texto",
                    "forma_fornecimento_texto",
                    default="Execucao continuada com postos dedicados e cobertura mensal.",
                ),
                "convencao_base": self._parameter_first(
                    parameter_values,
                    "cct_referencia",
                    "requisitos_tecnicos_itens",
                    default="Informar CCT/ACT, beneficios, encargos e premissas de insumos.",
                ),
                "repactuacao": self._parameter_first(
                    parameter_values,
                    "reajuste_revisao_texto",
                    default="Repactuacao e reajustes conforme legislacao e convencao aplicavel.",
                ),
                "medicao_texto": self._parameter_first(
                    parameter_values,
                    "pagamento_texto_tr",
                    default="Medicao mensal por posto efetivamente alocado e atestado.",
                ),
                "alocacao_texto": self._parameter_first(
                    parameter_values,
                    "recebimento_texto",
                    "forma_fornecimento_texto",
                    default="Alocacao por posto, turno e unidade atendida.",
                ),
            }
        )
        return metadata

    def _load_dataset(self, parameter_values, keys):
        for key in keys:
            raw_value = (parameter_values.get(key) or "").strip()
            if not raw_value:
                continue
            parsed_value = self._parse_json_value(raw_value)
            if parsed_value:
                return parsed_value
        return []

    def _parse_json_value(self, raw_value):
        if isinstance(raw_value, (list, dict)):
            return raw_value
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise UserError(
                (
                    "Foi encontrado um dataset de planilha, mas ele nao esta em JSON valido. "
                    f"Detalhe tecnico: {exc}"
                )
            ) from exc

    def _normalize_items(self, data):
        if isinstance(data, dict):
            data = data.get("items") or data.get("rows") or []
        if not isinstance(data, list):
            raise UserError("O dataset de itens da planilha deve ser uma lista JSON.")

        items = []
        for index, raw_item in enumerate(data, start=1):
            item = self._normalize_single_item(raw_item, fallback_index=index)
            if item:
                items.append(item)
        if not items:
            return []
        return sorted(items, key=self._item_sort_key)

    def _normalize_single_item(self, raw_item, fallback_index=1):
        if isinstance(raw_item, (list, tuple)):
            raw_item = {
                "lot_code": raw_item[0] if len(raw_item) > 0 else "",
                "item_number": raw_item[1] if len(raw_item) > 1 else fallback_index,
                "description": raw_item[2] if len(raw_item) > 2 else "",
                "unit": raw_item[3] if len(raw_item) > 3 else "Un",
                "monthly_quantity": raw_item[4] if len(raw_item) > 4 else 0,
                "annual_quantity": raw_item[5] if len(raw_item) > 5 else 0,
                "unit_price": raw_item[6] if len(raw_item) > 6 else 0,
                "class_abc": raw_item[7] if len(raw_item) > 7 else "",
                "lot_description": raw_item[8] if len(raw_item) > 8 else "",
                "specification": raw_item[9] if len(raw_item) > 9 else "",
            }
        elif not isinstance(raw_item, dict):
            raise UserError("Cada item da planilha deve ser um objeto JSON ou uma lista.")

        lot_code = self._string_value(
            raw_item,
            ("lot_code", "lote", "lote_codigo", "lot", "grupo"),
            default="1",
        )
        item_number = self._string_value(
            raw_item,
            ("item_number", "item", "numero_item", "sequencia"),
            default=str(fallback_index),
        )
        description = self._string_value(
            raw_item,
            ("description", "descricao", "objeto", "nome"),
        )
        if not description:
            return None

        monthly_quantity = self._float_value(
            raw_item,
            ("monthly_quantity", "qtde_mensal", "quantidade_mensal", "qtd_mes"),
        )
        annual_quantity = self._float_value(
            raw_item,
            ("annual_quantity", "qtde_anual", "quantidade_anual", "qtd_ano"),
        )
        if not annual_quantity and monthly_quantity:
            annual_quantity = monthly_quantity * 12
        if not monthly_quantity and annual_quantity:
            monthly_quantity = annual_quantity / 12.0

        unit_price = self._float_value(
            raw_item,
            ("unit_price", "preco_unitario", "preco_ref_unit", "valor_unitario"),
        )
        return {
            "lot_code": lot_code,
            "item_number": item_number,
            "class_abc": self._string_value(raw_item, ("class_abc", "classe_abc", "classe")),
            "lot_description": self._string_value(
                raw_item,
                ("lot_description", "lote_descricao", "descricao_lote", "grupo_descricao"),
            ),
            "description": description,
            "unit": self._string_value(raw_item, ("unit", "unidade", "un"), default="Un"),
            "monthly_quantity": monthly_quantity,
            "annual_quantity": annual_quantity,
            "unit_price": unit_price,
            "specification": self._string_value(
                raw_item,
                ("specification", "especificacao", "observacao", "nota"),
            ),
        }

    def _normalize_lots(self, data):
        if isinstance(data, dict):
            data = data.get("lots") or data.get("rows") or []
        if not isinstance(data, list):
            raise UserError("O dataset de lotes da planilha deve ser uma lista JSON.")

        lots = []
        for raw_lot in data:
            if not isinstance(raw_lot, dict):
                raise UserError("Cada lote da planilha deve ser um objeto JSON.")
            lot_code = self._string_value(raw_lot, ("lot_code", "lote", "codigo"), default="1")
            lots.append(
                {
                    "lot_code": lot_code,
                    "description": self._string_value(
                        raw_lot,
                        ("description", "descricao", "nome"),
                    ),
                    "class_abc": self._string_value(raw_lot, ("class_abc", "classe")),
                    "expected_value": self._float_value(
                        raw_lot,
                        ("expected_value", "valor_estimado", "valor_total"),
                    ),
                    "notes": self._string_value(raw_lot, ("notes", "observacoes", "nota")),
                }
            )
        return sorted(lots, key=lambda lot: self._sort_value(lot["lot_code"]))

    def _build_synthetic_items_from_lots(self, lots):
        synthetic_items = []
        for lot in lots:
            expected_value = lot.get("expected_value") or 0.0
            synthetic_items.append(
                {
                    "lot_code": lot["lot_code"],
                    "item_number": "1",
                    "class_abc": lot.get("class_abc") or "",
                    "lot_description": lot.get("description") or "",
                    "description": lot.get("description") or f"Lote {lot['lot_code']}",
                    "unit": "Lote",
                    "monthly_quantity": expected_value / 12.0 if expected_value else 0.0,
                    "annual_quantity": 1.0 if expected_value else 0.0,
                    "unit_price": expected_value,
                    "specification": (
                        "Item sintetico gerado a partir do resumo por lote. "
                        "Substitua pelo dataset detalhado para obter a planilha completa."
                    ),
                }
            )
        return synthetic_items

    def _merge_lots(self, items, explicit_lots):
        explicit_map = {lot["lot_code"]: lot for lot in explicit_lots}
        grouped = OrderedDict()
        for item in items:
            lot_code = item["lot_code"]
            group = grouped.setdefault(
                lot_code,
                {
                    "lot_code": lot_code,
                    "description": "",
                    "class_abc": "",
                    "item_count": 0,
                    "expected_value": 0.0,
                    "notes": "",
                },
            )
            group["item_count"] += 1
            group["expected_value"] += (item["annual_quantity"] or 0.0) * (item["unit_price"] or 0.0)
            if not group["description"]:
                group["description"] = item.get("lot_description") or item.get("description") or ""
            if not group["class_abc"]:
                group["class_abc"] = item.get("class_abc") or ""

        merged_lots = []
        for lot_code, aggregated in grouped.items():
            explicit = explicit_map.get(lot_code, {})
            merged_lots.append(
                {
                    "lot_code": lot_code,
                    "description": explicit.get("description") or aggregated["description"],
                    "class_abc": explicit.get("class_abc") or aggregated["class_abc"],
                    "item_count": aggregated["item_count"],
                    "expected_value": explicit.get("expected_value") or aggregated["expected_value"],
                    "notes": explicit.get("notes") or "",
                }
            )
        return sorted(merged_lots, key=lambda lot: self._sort_value(lot["lot_code"]))

    def _normalize_schedule(self, data, lots):
        if isinstance(data, dict):
            data = data.get("schedule") or data.get("rows") or []
        if data and not isinstance(data, list):
            raise UserError("O cronograma da planilha deve ser uma lista JSON.")

        schedule_map = {}
        for raw_row in data or []:
            if not isinstance(raw_row, dict):
                raise UserError("Cada linha do cronograma da planilha deve ser um objeto JSON.")
            lot_code = self._string_value(raw_row, ("lot_code", "lote", "codigo"), default="1")
            schedule_map[lot_code] = {
                month_key: self._string_value(raw_row, (month_key, month_label.lower()))
                for month_key, month_label in self._MONTHS
            }

        normalized = []
        for lot in lots:
            month_values = schedule_map.get(lot["lot_code"]) or self._build_default_schedule(lot)
            normalized.append(
                {
                    "lot_code": lot["lot_code"],
                    "description": lot["description"],
                    **month_values,
                }
            )
        return normalized

    def _build_default_schedule(self, lot):
        month_values = {month_key: "" for month_key, _month_label in self._MONTHS}
        class_abc = (lot.get("class_abc") or "").strip().upper()
        if class_abc == "A":
            pattern = {
                "jan": "OF 30-45 d",
                "mar": "OF 30-45 d",
                "mai": "OF 30-45 d",
                "jul": "OF 45-60 d",
                "out": "OF 30-45 d",
                "set": "OF 45-60 d",
                "nov": "OF 30 d",
                "dez": "OF 30 d",
            }
        elif class_abc == "B":
            pattern = {
                "jan": "OF 30-45 d",
                "mai": "OF 30-45 d",
                "set": "OF 45-60 d",
                "dez": "OF 30 d",
            }
        else:
            pattern = {
                "jan": "OF 30-45 d",
                "jul": "OF 45-60 d",
                "dez": "OF 30 d",
            }
        month_values.update(pattern)
        return month_values

    def _render_procurement_workbook(self, payload):
        try:
            import xlsxwriter
        except ImportError as exc:
            raise UserError(
                "O pacote Python 'xlsxwriter' nao esta instalado no ambiente do Odoo."
            ) from exc

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        formats = self._build_formats(workbook)
        self._write_items_sheet(workbook, payload, formats)
        self._write_lot_summary_sheet(workbook, payload, formats)
        self._write_schedule_sheet(workbook, payload, formats)

        workbook.close()
        return output.getvalue()

    def _render_service_continuous_workbook(self, payload):
        try:
            import xlsxwriter
        except ImportError as exc:
            raise UserError(
                "O pacote Python 'xlsxwriter' nao esta instalado no ambiente do Odoo."
            ) from exc

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        formats = self._build_formats(workbook)
        self._write_service_posts_sheet(workbook, payload, formats)
        self._write_service_summary_sheet(workbook, payload, formats)
        self._write_service_coverage_sheet(workbook, payload, formats)

        workbook.close()
        return output.getvalue()

    def _build_formats(self, workbook):
        return {
            "title": workbook.add_format(
                {
                    "bold": True,
                    "font_size": 14,
                    "font_color": "#FFFFFF",
                    "align": "center",
                    "valign": "vcenter",
                    "bg_color": "#1A3A5C",
                }
            ),
            "subtitle": workbook.add_format(
                {
                    "italic": True,
                    "font_color": "#1A3A5C",
                    "align": "center",
                    "bg_color": "#D6E4F0",
                }
            ),
            "context": workbook.add_format(
                {
                    "font_color": "#1A3A5C",
                    "align": "center",
                    "bg_color": "#EBF3FB",
                }
            ),
            "legend": workbook.add_format(
                {
                    "font_color": "#334155",
                    "align": "center",
                    "bg_color": "#F8FAFC",
                }
            ),
            "header": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#1A3A5C",
                    "font_color": "#FFFFFF",
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "text_wrap": True,
                }
            ),
            "header_cheia": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#DBEAFE",
                    "font_color": "#1E3A8A",
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "text_wrap": True,
                }
            ),
            "header_seca": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#FFEDD5",
                    "font_color": "#9A3412",
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "text_wrap": True,
                }
            ),
            "header_trans": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#DCFCE7",
                    "font_color": "#166534",
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "text_wrap": True,
                }
            ),
            "lot_band": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#D6E4F0",
                    "font_color": "#1A3A5C",
                    "border": 1,
                    "valign": "vcenter",
                }
            ),
            "cell": workbook.add_format({"border": 1, "valign": "top"}),
            "cell_center": workbook.add_format(
                {"border": 1, "valign": "vcenter", "align": "center"}
            ),
            "text_wrap": workbook.add_format({"border": 1, "valign": "top", "text_wrap": True}),
            "number": workbook.add_format({"border": 1, "num_format": "#,##0.00"}),
            "currency": workbook.add_format({"border": 1, "num_format": "R$ #,##0.00"}),
            "percent": workbook.add_format({"border": 1, "num_format": "0.00%"}),
            "integer": workbook.add_format({"border": 1, "num_format": "#,##0"}),
            "class_a": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bold": True,
                    "bg_color": "#D6E4F0",
                    "font_color": "#1A3A5C",
                }
            ),
            "class_b": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bold": True,
                    "bg_color": "#FEE2E2",
                    "font_color": "#991B1B",
                }
            ),
            "class_c": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bold": True,
                    "bg_color": "#E5E7EB",
                    "font_color": "#374151",
                }
            ),
            "meta_label": workbook.add_format(
                {"bold": True, "bg_color": "#D6E4F0", "border": 1}
            ),
            "meta_value": workbook.add_format({"border": 1, "text_wrap": True}),
            "total_label": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#1A3A5C",
                    "font_color": "#FFFFFF",
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                }
            ),
            "total_currency": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#1A3A5C",
                    "font_color": "#FFFFFF",
                    "border": 1,
                    "num_format": "R$ #,##0.00",
                }
            ),
            "total_percent": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#1A3A5C",
                    "font_color": "#FFFFFF",
                    "border": 1,
                    "num_format": "0.00%",
                }
            ),
            "schedule_label": workbook.add_format(
                {
                    "border": 1,
                    "text_wrap": True,
                    "valign": "vcenter",
                }
            ),
            "schedule_cheia": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "text_wrap": True,
                    "bg_color": "#EFF6FF",
                }
            ),
            "schedule_seca": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "text_wrap": True,
                    "bg_color": "#FFF7ED",
                }
            ),
            "schedule_trans": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "text_wrap": True,
                    "bg_color": "#F0FDF4",
                }
            ),
            "footnote": workbook.add_format(
                {
                    "italic": True,
                    "align": "center",
                    "valign": "vcenter",
                    "text_wrap": True,
                    "bg_color": "#F8FAFC",
                }
            ),
        }

    def _write_items_sheet(self, workbook, payload, formats):
        worksheet = workbook.add_worksheet("Itens da Licitacao")
        metadata = payload["metadata"]
        items = payload["items"]
        lots = payload["lots"]

        grouped_items = OrderedDict((lot["lot_code"], []) for lot in lots)
        for item in items:
            grouped_items.setdefault(item["lot_code"], []).append(item)

        worksheet.merge_range("A1:M1", metadata["header_orgao"], formats["title"])
        worksheet.merge_range("A2:M2", metadata["header_reference_line"], formats["subtitle"])
        worksheet.merge_range("A3:M3", metadata["header_subject_line"], formats["context"])
        worksheet.merge_range("A4:M4", "", formats["context"])
        worksheet.merge_range("A5:M5", metadata["legend_line"], formats["legend"])
        worksheet.merge_range("A6:M6", "", formats["legend"])
        headers = [
            "Lote",
            "Item",
            "Classe",
            "Descricao do Item",
            "Un.",
            "Qtde./mes",
            "Qtde. anual",
            "Pr. Ref. Unit. (R$)",
            "Valor Mensal (R$)",
            "Valor Anual (R$)",
            "% do lote",
            "% do total",
            "Especificacao Tecnica Resumida",
        ]
        worksheet.write_row(6, 0, headers, formats["header"])
        worksheet.freeze_panes(7, 0)
        worksheet.set_column("A:A", 5)
        worksheet.set_column("B:B", 5)
        worksheet.set_column("C:C", 6)
        worksheet.set_column("D:D", 46)
        worksheet.set_column("E:E", 6)
        worksheet.set_column("F:F", 10)
        worksheet.set_column("G:G", 12)
        worksheet.set_column("H:J", 13)
        worksheet.set_column("K:L", 9)
        worksheet.set_column("M:M", 46)

        worksheet.set_row(0, 22)
        worksheet.set_row(1, 18)
        worksheet.set_row(2, 18)
        worksheet.set_row(3, 8)
        worksheet.set_row(4, 16)
        worksheet.set_row(5, 6)
        worksheet.set_row(6, 36)

        detail_first_excel_row = 9
        detail_last_excel_row = 7 + len(lots) + len(items)
        row_index = 7
        for lot in lots:
            lot_items = grouped_items.get(lot["lot_code"]) or []
            if not lot_items:
                continue
            lot_value = lot.get("expected_value") or 0.0
            banner_text = (
                f"{self._format_lot_code_label(lot['lot_code'])} - "
                f"{lot.get('description') or 'Sem descricao'} - "
                f"Valor estimado: {self._format_currency_brl(lot_value)}"
            )
            worksheet.merge_range(row_index, 0, row_index, 12, banner_text, formats["lot_band"])
            worksheet.set_row(row_index, 17)
            row_index += 1

            lot_first_excel_row = row_index + 1
            lot_last_excel_row = row_index + len(lot_items)
            for item in lot_items:
                excel_row = row_index + 1
                worksheet.set_row(row_index, 32)
                worksheet.write(row_index, 0, item["lot_code"], formats["cell_center"])
                worksheet.write(row_index, 1, item["item_number"], formats["cell_center"])
                worksheet.write(
                    row_index,
                    2,
                    item["class_abc"],
                    self._get_class_format(formats, item.get("class_abc")),
                )
                worksheet.write(row_index, 3, item["description"], formats["text_wrap"])
                worksheet.write(row_index, 4, item["unit"], formats["cell_center"])
                worksheet.write_number(row_index, 5, item["monthly_quantity"], formats["integer"])
                worksheet.write_number(row_index, 6, item["annual_quantity"], formats["integer"])
                worksheet.write_number(row_index, 7, item["unit_price"], formats["currency"])
                worksheet.write_formula(row_index, 8, f"=F{excel_row}*H{excel_row}", formats["currency"])
                worksheet.write_formula(row_index, 9, f"=G{excel_row}*H{excel_row}", formats["currency"])
                worksheet.write_formula(
                    row_index,
                    10,
                    f"=IFERROR(J{excel_row}/SUM(J{lot_first_excel_row}:J{lot_last_excel_row}),0)",
                    formats["percent"],
                )
                worksheet.write_formula(
                    row_index,
                    11,
                    f"=IFERROR(J{excel_row}/SUM($J${detail_first_excel_row}:$J${detail_last_excel_row}),0)",
                    formats["percent"],
                )
                worksheet.write(row_index, 12, item["specification"], formats["text_wrap"])
                row_index += 1

        worksheet.autofilter(6, 0, detail_last_excel_row - 1, 12)
        worksheet.set_row(row_index, 8)
        row_index += 1
        total_label = (
            f"TOTAL GERAL ({metadata['total_itens']} itens - "
            f"{metadata['total_lotes']} lotes - 12 meses)"
        )
        worksheet.merge_range(row_index, 0, row_index, 7, total_label, formats["total_label"])
        worksheet.write_formula(
            row_index,
            8,
            f"=SUM(I{detail_first_excel_row}:I{detail_last_excel_row})",
            formats["total_currency"],
        )
        worksheet.write_formula(
            row_index,
            9,
            f"=SUM(J{detail_first_excel_row}:J{detail_last_excel_row})",
            formats["total_currency"],
        )
        worksheet.write_string(row_index, 10, "100%", formats["total_label"])
        worksheet.write_string(row_index, 11, "100%", formats["total_label"])
        worksheet.write(row_index, 12, "", formats["total_label"])
        worksheet.set_row(row_index, 22)

    def _write_lot_summary_sheet(self, workbook, payload, formats):
        worksheet = workbook.add_worksheet("Resumo por Lote")
        metadata = payload["metadata"]
        lots = payload["lots"]

        worksheet.merge_range("A1:G1", metadata["summary_title"], formats["title"])
        worksheet.merge_range("A2:G2", metadata["summary_subtitle"], formats["subtitle"])
        worksheet.merge_range("A3:G3", "", formats["context"])
        headers = [
            "Lote",
            "Descricao do Lote",
            "Classe",
            "N.o Itens",
            "Valor Estimado (R$)",
            "% do total",
            "Modalidade / Observacoes",
        ]
        worksheet.write_row(3, 0, headers, formats["header"])
        worksheet.set_column("A:A", 6)
        worksheet.set_column("B:B", 38)
        worksheet.set_column("C:C", 8)
        worksheet.set_column("D:D", 8)
        worksheet.set_column("E:E", 18)
        worksheet.set_column("F:F", 10)
        worksheet.set_column("G:G", 28)

        worksheet.set_row(0, 22)
        worksheet.set_row(1, 18)
        worksheet.set_row(2, 10)
        worksheet.set_row(3, 28)

        item_first_row = 9
        item_last_row = 7 + len(payload["items"]) + len(lots)
        first_lot_row = 5
        last_lot_row = len(lots) + 4
        total_row = len(lots) + 4
        total_excel_row = total_row + 1
        for offset, lot in enumerate(lots, start=4):
            excel_row = offset + 1
            worksheet.set_row(offset, 18)
            worksheet.write(offset, 0, lot["lot_code"], formats["cell_center"])
            worksheet.write(offset, 1, lot["description"], formats["text_wrap"])
            worksheet.write(
                offset,
                2,
                lot["class_abc"],
                self._get_class_format(formats, lot.get("class_abc")),
            )
            worksheet.write_formula(
                offset,
                3,
                (
                    f"=COUNTIF('Itens da Licitacao'!$A${item_first_row}:$A${item_last_row},"
                    f"A{excel_row})"
                ),
                formats["integer"],
            )
            worksheet.write_formula(
                offset,
                4,
                (
                    f"=SUMIF('Itens da Licitacao'!$A${item_first_row}:$A${item_last_row},"
                    f"A{excel_row},'Itens da Licitacao'!$J${item_first_row}:$J${item_last_row})"
                ),
                formats["currency"],
            )
            worksheet.write_formula(
                offset,
                5,
                f"=IFERROR(E{excel_row}/$E${total_excel_row},0)",
                formats["percent"],
            )
            worksheet.write(
                offset,
                6,
                self._lot_modality_display(metadata, lot),
                formats["text_wrap"],
            )

        worksheet.merge_range(total_row, 0, total_row, 3, "TOTAL GERAL", formats["total_label"])
        worksheet.write_formula(
            total_row,
            4,
            f"=SUM(E{first_lot_row}:E{last_lot_row})",
            formats["total_currency"],
        )
        worksheet.write_formula(
            total_row,
            5,
            f"=SUM(F{first_lot_row}:F{last_lot_row})",
            formats["total_percent"],
        )
        worksheet.write(total_row, 6, "", formats["total_label"])
        worksheet.set_row(total_row, 20)

        meta_row = total_row + 2
        meta_pairs = [
            ("Numero do TR", metadata["referencia_numero"]),
            ("Modalidade", metadata["modalidade"]),
            ("Criterio de julgamento", metadata["criterio_julgamento"]),
            ("Vigencia da ARP", metadata["vigencia_arp"]),
            ("Entrega", metadata["entrega"]),
            ("Total de lotes", str(metadata["total_lotes"])),
            ("Total de itens", str(metadata["total_itens"])),
            ("Valor total estimado", metadata["valor_total_display"]),
            ("Registro ANVISA", metadata["anvisa_note"]),
            ("Base legal", metadata["base_legal"]),
            ("Elaborado por", metadata["elaborated_by"]),
        ]
        for label, value in meta_pairs:
            worksheet.write(meta_row, 0, label, formats["meta_label"])
            worksheet.merge_range(meta_row, 1, meta_row, 6, value or "-", formats["meta_value"])
            worksheet.set_row(meta_row, 16)
            meta_row += 1

    def _write_schedule_sheet(self, workbook, payload, formats):
        worksheet = workbook.add_worksheet("Cronograma de Pedidos")
        metadata = payload["metadata"]
        lot_map = {lot["lot_code"]: lot for lot in payload["lots"]}

        worksheet.merge_range("A1:M1", metadata["schedule_title"], formats["title"])
        worksheet.merge_range("A2:M2", metadata["schedule_subtitle"], formats["subtitle"])
        worksheet.merge_range("A3:M3", "", formats["context"])
        headers = ["Lote / Item"] + [
            self._schedule_header_label(month_key, month_label)
            for month_key, month_label in self._MONTHS
        ]
        worksheet.write(3, 0, headers[0], formats["header"])
        for column, (month_key, _month_label) in enumerate(self._MONTHS, start=1):
            worksheet.write(
                3,
                column,
                headers[column],
                self._schedule_header_format(formats, month_key),
            )
        worksheet.set_column("A:A", 34)
        worksheet.set_column("B:M", 9)
        worksheet.set_row(0, 22)
        worksheet.set_row(1, 16)
        worksheet.set_row(2, 8)
        worksheet.set_row(3, 32)

        row_index = 4
        for schedule_row in payload["schedule"]:
            lot = lot_map.get(schedule_row["lot_code"], {})
            class_abc = lot.get("class_abc") or ""
            worksheet.write(
                row_index,
                0,
                (
                    f"{self._format_lot_code_label(schedule_row['lot_code'])} - "
                    f"{schedule_row['description']} (Cl. {class_abc or '-'})"
                ),
                formats["schedule_label"],
            )
            worksheet.set_row(row_index, 28)
            for column, (month_key, _month_label) in enumerate(self._MONTHS, start=1):
                worksheet.write(
                    row_index,
                    column,
                    schedule_row.get(month_key) or "-",
                    self._schedule_cell_format(formats, month_key),
                )
            row_index += 1

        worksheet.set_row(row_index, 8)
        row_index += 1
        worksheet.merge_range(
            row_index,
            0,
            row_index,
            12,
            (
                "OF = Ordem de Fornecimento emitida com antecedencia minima de 20 dias. "
                "Cheia: cobertura de 30-45 dias. Seca: cobertura de 45-60 dias. "
                "Transicao: cobertura de 30 dias."
            ),
            formats["footnote"],
        )
        worksheet.set_row(row_index, 16)

    def _write_service_posts_sheet(self, workbook, payload, formats):
        worksheet = workbook.add_worksheet("Postos e Custos")
        metadata = payload["metadata"]
        items = payload["items"]
        lots = payload["lots"]

        grouped_items = OrderedDict((lot["lot_code"], []) for lot in lots)
        for item in items:
            grouped_items.setdefault(item["lot_code"], []).append(item)

        worksheet.merge_range("A1:L1", metadata["header_orgao"], formats["title"])
        worksheet.merge_range("A2:L2", metadata["header_reference_line"], formats["subtitle"])
        worksheet.merge_range("A3:L3", metadata["header_subject_line"], formats["context"])
        worksheet.merge_range("A4:L4", "", formats["context"])
        worksheet.merge_range("A5:L5", metadata["legend_line"], formats["legend"])
        worksheet.merge_range("A6:L6", "", formats["legend"])
        headers = [
            "Lote",
            "Posto",
            "Perfil / Funcao",
            "Un.",
            "Qtd. Postos",
            "Meses",
            "Custo Mensal Unit. (R$)",
            "Custo Mensal (R$)",
            "Custo Anual (R$)",
            "Escala / Cobertura",
            "CCT / Base",
            "Observacoes",
        ]
        worksheet.write_row(6, 0, headers, formats["header"])
        worksheet.freeze_panes(7, 0)
        worksheet.set_column("A:A", 5)
        worksheet.set_column("B:B", 7)
        worksheet.set_column("C:C", 34)
        worksheet.set_column("D:D", 7)
        worksheet.set_column("E:F", 10)
        worksheet.set_column("G:I", 16)
        worksheet.set_column("J:L", 26)

        worksheet.set_row(0, 22)
        worksheet.set_row(1, 18)
        worksheet.set_row(2, 18)
        worksheet.set_row(3, 8)
        worksheet.set_row(4, 16)
        worksheet.set_row(5, 6)
        worksheet.set_row(6, 36)

        detail_first_excel_row = 9
        detail_last_excel_row = 7 + len(lots) + len(items)
        row_index = 7
        for lot in lots:
            lot_items = grouped_items.get(lot["lot_code"]) or []
            if not lot_items:
                continue
            banner_text = (
                f"{self._format_lot_code_label(lot['lot_code'])} - "
                f"{lot.get('description') or 'Grupo de postos'} - "
                f"Custo anual estimado: {self._format_currency_brl(lot.get('expected_value') or 0.0)}"
            )
            worksheet.merge_range(row_index, 0, row_index, 11, banner_text, formats["lot_band"])
            worksheet.set_row(row_index, 17)
            row_index += 1

            for item in lot_items:
                months_base = (
                    (item["annual_quantity"] / item["monthly_quantity"])
                    if item["monthly_quantity"]
                    else 12.0
                )
                worksheet.set_row(row_index, 32)
                worksheet.write(row_index, 0, item["lot_code"], formats["cell_center"])
                worksheet.write(row_index, 1, item["item_number"], formats["cell_center"])
                worksheet.write(row_index, 2, item["description"], formats["text_wrap"])
                worksheet.write(row_index, 3, item["unit"] or "Posto", formats["cell_center"])
                worksheet.write_number(row_index, 4, item["monthly_quantity"], formats["integer"])
                worksheet.write_number(row_index, 5, months_base, formats["integer"])
                worksheet.write_number(row_index, 6, item["unit_price"], formats["currency"])
                excel_row = row_index + 1
                worksheet.write_formula(row_index, 7, f"=E{excel_row}*G{excel_row}", formats["currency"])
                worksheet.write_formula(row_index, 8, f"=H{excel_row}*F{excel_row}", formats["currency"])
                worksheet.write(row_index, 9, item["lot_description"] or "", formats["text_wrap"])
                worksheet.write(row_index, 10, item["specification"] or "", formats["text_wrap"])
                worksheet.write(
                    row_index,
                    11,
                    f"Classe {item['class_abc'] or '-'}",
                    self._get_class_format(formats, item.get("class_abc")),
                )
                row_index += 1

        worksheet.autofilter(6, 0, detail_last_excel_row - 1, 11)
        worksheet.set_row(row_index, 8)
        row_index += 1
        total_label = (
            f"TOTAL DO CONTRATO ({metadata['total_itens']} postos/itens - "
            f"{metadata['total_lotes']} grupos)"
        )
        worksheet.merge_range(row_index, 0, row_index, 6, total_label, formats["total_label"])
        worksheet.write_formula(
            row_index,
            7,
            f"=SUM(H{detail_first_excel_row}:H{detail_last_excel_row})",
            formats["total_currency"],
        )
        worksheet.write_formula(
            row_index,
            8,
            f"=SUM(I{detail_first_excel_row}:I{detail_last_excel_row})",
            formats["total_currency"],
        )
        worksheet.merge_range(row_index, 9, row_index, 11, "", formats["total_label"])
        worksheet.set_row(row_index, 22)

    def _write_service_summary_sheet(self, workbook, payload, formats):
        worksheet = workbook.add_worksheet("Resumo do Contrato")
        metadata = payload["metadata"]
        lots = payload["lots"]

        worksheet.merge_range("A1:G1", metadata["summary_title"], formats["title"])
        worksheet.merge_range("A2:G2", metadata["summary_subtitle"], formats["subtitle"])
        worksheet.merge_range("A3:G3", "", formats["context"])
        headers = [
            "Lote",
            "Grupo / Categoria",
            "Qtd. Postos",
            "Meses Base",
            "Custo Mensal (R$)",
            "Custo Anual (R$)",
            "% do Contrato",
        ]
        worksheet.write_row(3, 0, headers, formats["header"])
        worksheet.set_column("A:A", 6)
        worksheet.set_column("B:B", 38)
        worksheet.set_column("C:D", 10)
        worksheet.set_column("E:F", 18)
        worksheet.set_column("G:G", 12)

        worksheet.set_row(0, 22)
        worksheet.set_row(1, 18)
        worksheet.set_row(2, 10)
        worksheet.set_row(3, 28)

        item_first_row = 9
        item_last_row = 7 + len(payload["items"]) + len(lots)
        first_lot_row = 5
        last_lot_row = len(lots) + 4
        total_row = len(lots) + 4
        total_excel_row = total_row + 1
        for offset, lot in enumerate(lots, start=4):
            excel_row = offset + 1
            worksheet.set_row(offset, 18)
            worksheet.write(offset, 0, lot["lot_code"], formats["cell_center"])
            worksheet.write(offset, 1, lot["description"], formats["text_wrap"])
            worksheet.write_formula(
                offset,
                2,
                (
                    f"=SUMIF('Postos e Custos'!$A${item_first_row}:$A${item_last_row},"
                    f"A{excel_row},'Postos e Custos'!$E${item_first_row}:$E${item_last_row})"
                ),
                formats["integer"],
            )
            worksheet.write_formula(
                offset,
                3,
                (
                    f"=IFERROR(AVERAGEIF('Postos e Custos'!$A${item_first_row}:$A${item_last_row},"
                    f"A{excel_row},'Postos e Custos'!$F${item_first_row}:$F${item_last_row}),12)"
                ),
                formats["integer"],
            )
            worksheet.write_formula(
                offset,
                4,
                (
                    f"=SUMIF('Postos e Custos'!$A${item_first_row}:$A${item_last_row},"
                    f"A{excel_row},'Postos e Custos'!$H${item_first_row}:$H${item_last_row})"
                ),
                formats["currency"],
            )
            worksheet.write_formula(
                offset,
                5,
                (
                    f"=SUMIF('Postos e Custos'!$A${item_first_row}:$A${item_last_row},"
                    f"A{excel_row},'Postos e Custos'!$I${item_first_row}:$I${item_last_row})"
                ),
                formats["currency"],
            )
            worksheet.write_formula(
                offset,
                6,
                f"=IFERROR(F{excel_row}/$F${total_excel_row},0)",
                formats["percent"],
            )

        worksheet.merge_range(total_row, 0, total_row, 3, "TOTAL DO CONTRATO", formats["total_label"])
        worksheet.write_formula(
            total_row,
            4,
            f"=SUM(E{first_lot_row}:E{last_lot_row})",
            formats["total_currency"],
        )
        worksheet.write_formula(
            total_row,
            5,
            f"=SUM(F{first_lot_row}:F{last_lot_row})",
            formats["total_currency"],
        )
        worksheet.write_formula(
            total_row,
            6,
            f"=SUM(G{first_lot_row}:G{last_lot_row})",
            formats["total_percent"],
        )
        worksheet.set_row(total_row, 20)

        meta_row = total_row + 2
        meta_pairs = [
            ("Modalidade", metadata["modalidade"]),
            ("Regime de execucao", metadata["regime_execucao"]),
            ("Vigencia", metadata["vigencia_arp"]),
            ("Repactuacao / reajuste", metadata["repactuacao"]),
            ("Medicao e pagamento", metadata["medicao_texto"]),
            ("Convencao / base tecnica", metadata["convencao_base"]),
            ("Alocacao / cobertura", metadata["alocacao_texto"]),
            ("Valor total estimado", metadata["valor_total_display"]),
        ]
        for label, value in meta_pairs:
            worksheet.write(meta_row, 0, label, formats["meta_label"])
            worksheet.merge_range(meta_row, 1, meta_row, 6, value or "-", formats["meta_value"])
            worksheet.set_row(meta_row, 16)
            meta_row += 1

    def _write_service_coverage_sheet(self, workbook, payload, formats):
        worksheet = workbook.add_worksheet("Cobertura e Medicao")
        metadata = payload["metadata"]
        lot_map = {lot["lot_code"]: lot for lot in payload["lots"]}

        worksheet.merge_range("A1:M1", metadata["schedule_title"], formats["title"])
        worksheet.merge_range("A2:M2", metadata["schedule_subtitle"], formats["subtitle"])
        worksheet.merge_range("A3:M3", "", formats["context"])
        headers = ["Lote / Cobertura"] + [
            self._schedule_header_label(month_key, month_label)
            for month_key, month_label in self._MONTHS
        ]
        worksheet.write(3, 0, headers[0], formats["header"])
        for column, (month_key, _month_label) in enumerate(self._MONTHS, start=1):
            worksheet.write(
                3,
                column,
                headers[column],
                self._schedule_header_format(formats, month_key),
            )
        worksheet.set_column("A:A", 34)
        worksheet.set_column("B:M", 11)
        worksheet.set_row(0, 22)
        worksheet.set_row(1, 16)
        worksheet.set_row(2, 8)
        worksheet.set_row(3, 32)

        row_index = 4
        for schedule_row in payload["schedule"]:
            lot = lot_map.get(schedule_row["lot_code"], {})
            worksheet.write(
                row_index,
                0,
                (
                    f"{self._format_lot_code_label(schedule_row['lot_code'])} - "
                    f"{schedule_row['description']} (Cl. {lot.get('class_abc') or '-'})"
                ),
                formats["schedule_label"],
            )
            worksheet.set_row(row_index, 28)
            for column, (month_key, _month_label) in enumerate(self._MONTHS, start=1):
                worksheet.write(
                    row_index,
                    column,
                    schedule_row.get(month_key) or "-",
                    self._schedule_cell_format(formats, month_key),
                )
            row_index += 1

        worksheet.set_row(row_index, 8)
        row_index += 1
        worksheet.merge_range(
            row_index,
            0,
            row_index,
            12,
            (
                "Use os meses para sinalizar cobertura de ferias, reservas tecnicas, "
                "substituicoes, janelas de fiscalizacao e medicao mensal."
            ),
            formats["footnote"],
        )
        worksheet.set_row(row_index, 16)

    def _format_lot_code_label(self, lot_code):
        text = str(lot_code or "").strip()
        if text.isdigit():
            return f"LOTE {int(text):02d}"
        return f"LOTE {text}"

    def _get_class_format(self, formats, class_abc):
        class_abc = (class_abc or "").strip().upper()
        if class_abc == "A":
            return formats["class_a"]
        if class_abc == "B":
            return formats["class_b"]
        return formats["class_c"]

    def _lot_modality_display(self, metadata, lot):
        notes = (lot.get("notes") or "").strip()
        if notes:
            return f"{metadata['modalidade']} | {notes}"
        return metadata["modalidade"]

    def _schedule_header_label(self, month_key, month_label):
        season_map = {
            "jan": "CHEIA",
            "fev": "CHEIA",
            "mar": "CHEIA",
            "abr": "CHEIA",
            "mai": "CHEIA",
            "jun": "CHEIA",
            "jul": "SECA",
            "ago": "SECA",
            "set": "SECA",
            "out": "SECA",
            "nov": "TRANS.",
            "dez": "TRANS.",
        }
        return f"{month_label}\n({season_map[month_key]})"

    def _schedule_header_format(self, formats, month_key):
        season = self._schedule_season(month_key)
        if season == "cheia":
            return formats["header_cheia"]
        if season == "seca":
            return formats["header_seca"]
        return formats["header_trans"]

    def _schedule_cell_format(self, formats, month_key):
        season = self._schedule_season(month_key)
        if season == "cheia":
            return formats["schedule_cheia"]
        if season == "seca":
            return formats["schedule_seca"]
        return formats["schedule_trans"]

    def _schedule_season(self, month_key):
        if month_key in {"jan", "fev", "mar", "abr", "mai", "jun"}:
            return "cheia"
        if month_key in {"jul", "ago", "set", "out"}:
            return "seca"
        return "trans"

    def _item_sort_key(self, item):
        return (
            self._sort_value(item["lot_code"]),
            self._sort_value(item["item_number"]),
        )

    def _sort_value(self, value):
        text = str(value or "").strip()
        if text.isdigit():
            return (0, int(text))
        return (1, text)

    def _string_value(self, data, keys, default=""):
        for key in keys:
            value = data.get(key)
            if value not in (None, ""):
                return str(value).strip()
        return default

    def _float_value(self, data, keys):
        for key in keys:
            value = data.get(key)
            if value in (None, ""):
                continue
            if isinstance(value, (int, float)):
                return float(value)
            normalized = str(value).strip()
            if "," in normalized and "." in normalized:
                normalized = normalized.replace(".", "").replace(",", ".")
            elif "," in normalized:
                normalized = normalized.replace(",", ".")
            try:
                return float(normalized)
            except ValueError:
                continue
        return 0.0
