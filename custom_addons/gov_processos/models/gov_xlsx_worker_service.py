import hashlib
import io
import json
from collections import OrderedDict

from odoo import models
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

    def generate_procurement_workbook(self, processo, doc=None):
        payload = self.build_procurement_payload(processo, doc=doc)
        workbook_binary = self._render_procurement_workbook(payload)
        filename = self._build_filename(processo, doc)
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

        return {
            "metadata": {
                "processo_numero": processo.name or "",
                "processo_assunto": processo.subject or "",
                "process_scope": processo.process_scope or "",
                "process_type": processo.process_type or "",
                "doc_nome": doc.name if doc else "",
                "doc_tipo": doc.doc_type if doc else "",
                "documento_referencia": doc.ai_template_id.name if doc and doc.ai_template_id else "",
                "valor_total_estimado": processo.valor_total_estimado or 0.0,
            },
            "items": items,
            "lots": lots,
            "schedule": schedule,
        }

    def _build_filename(self, processo, doc=None):
        doc_type = (doc.doc_type if doc else "processo") or "processo"
        process_number = (processo.name or "processo").replace("/", "-").replace(" ", "_")
        return f"{doc_type}_{process_number}_planilha.xlsx"

    def _get_parameter_values(self, processo):
        values = {}
        for parameter in processo.parameter_ids:
            values[parameter.key] = parameter.value_text or ""
        return values

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
            selected_months = ("jan", "abr", "jul", "out")
            label = "OF 30-45 d"
        elif class_abc == "B":
            selected_months = ("fev", "jun", "set")
            label = "OF 45-60 d"
        else:
            selected_months = ("mar", "ago", "nov")
            label = "OF 60-90 d"
        for month_key in selected_months:
            month_values[month_key] = label
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

    def _build_formats(self, workbook):
        return {
            "title": workbook.add_format(
                {
                    "bold": True,
                    "font_size": 14,
                    "font_color": "#1A3A5C",
                    "align": "center",
                    "valign": "vcenter",
                }
            ),
            "subtitle": workbook.add_format(
                {
                    "italic": True,
                    "font_color": "#475569",
                    "align": "center",
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
            "cell": workbook.add_format({"border": 1, "valign": "top"}),
            "cell_alt": workbook.add_format(
                {"border": 1, "valign": "top", "bg_color": "#EBF3FB"}
            ),
            "text_wrap": workbook.add_format({"border": 1, "valign": "top", "text_wrap": True}),
            "text_wrap_alt": workbook.add_format(
                {"border": 1, "valign": "top", "text_wrap": True, "bg_color": "#EBF3FB"}
            ),
            "number": workbook.add_format({"border": 1, "num_format": "#,##0.00"}),
            "number_alt": workbook.add_format(
                {"border": 1, "num_format": "#,##0.00", "bg_color": "#EBF3FB"}
            ),
            "percent": workbook.add_format({"border": 1, "num_format": "0.00%"}),
            "percent_alt": workbook.add_format(
                {"border": 1, "num_format": "0.00%", "bg_color": "#EBF3FB"}
            ),
            "integer": workbook.add_format({"border": 1, "num_format": "#,##0"}),
            "integer_alt": workbook.add_format(
                {"border": 1, "num_format": "#,##0", "bg_color": "#EBF3FB"}
            ),
            "meta_label": workbook.add_format(
                {"bold": True, "bg_color": "#D6E4F0", "border": 1}
            ),
            "meta_value": workbook.add_format({"border": 1}),
            "total_label": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#D6E4F0",
                    "border": 1,
                    "align": "right",
                }
            ),
            "total_number": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#D6E4F0",
                    "border": 1,
                    "num_format": "#,##0.00",
                }
            ),
            "total_percent": workbook.add_format(
                {
                    "bold": True,
                    "bg_color": "#D6E4F0",
                    "border": 1,
                    "num_format": "0.00%",
                }
            ),
            "schedule_mark": workbook.add_format(
                {
                    "border": 1,
                    "align": "center",
                    "valign": "vcenter",
                    "bg_color": "#EBF3FB",
                }
            ),
        }

    def _write_items_sheet(self, workbook, payload, formats):
        worksheet = workbook.add_worksheet("Itens da Licitacao")
        metadata = payload["metadata"]
        items = payload["items"]

        worksheet.merge_range(
            "A1:M1",
            "Planilha de Itens da Licitacao",
            formats["title"],
        )
        worksheet.merge_range(
            "A2:M2",
            f"Processo {metadata['processo_numero']} | {metadata['processo_assunto']}",
            formats["subtitle"],
        )
        headers = [
            "Lote",
            "Item",
            "Classe ABC",
            "Descricao",
            "Un.",
            "Qtde./mes",
            "Qtde. anual",
            "Preco ref. unit. (R$)",
            "Valor mensal",
            "Valor anual",
            "% do lote",
            "% do total",
            "Especificacao tecnica minima",
        ]
        worksheet.write_row(3, 0, headers, formats["header"])
        worksheet.freeze_panes(4, 0)
        worksheet.autofilter(3, 0, 3 + len(items), len(headers) - 1)
        worksheet.set_column("A:A", 8)
        worksheet.set_column("B:B", 8)
        worksheet.set_column("C:C", 12)
        worksheet.set_column("D:D", 42)
        worksheet.set_column("E:E", 8)
        worksheet.set_column("F:G", 14)
        worksheet.set_column("H:J", 18)
        worksheet.set_column("K:L", 12)
        worksheet.set_column("M:M", 44)

        first_excel_row = 5
        last_excel_row = len(items) + 4
        for offset, item in enumerate(items, start=4):
            excel_row = offset + 1
            alt = (offset - 4) % 2 == 0
            cell_format = formats["cell_alt"] if alt else formats["cell"]
            integer_format = formats["integer_alt"] if alt else formats["integer"]
            number_format = formats["number_alt"] if alt else formats["number"]
            percent_format = formats["percent_alt"] if alt else formats["percent"]
            wrap_format = formats["text_wrap_alt"] if alt else formats["text_wrap"]

            worksheet.write(offset, 0, item["lot_code"], cell_format)
            worksheet.write(offset, 1, item["item_number"], cell_format)
            worksheet.write(offset, 2, item["class_abc"], cell_format)
            worksheet.write(offset, 3, item["description"], wrap_format)
            worksheet.write(offset, 4, item["unit"], cell_format)
            worksheet.write_number(offset, 5, item["monthly_quantity"], integer_format)
            worksheet.write_number(offset, 6, item["annual_quantity"], integer_format)
            worksheet.write_number(offset, 7, item["unit_price"], number_format)
            worksheet.write_formula(offset, 8, f"=F{excel_row}*H{excel_row}", number_format)
            worksheet.write_formula(offset, 9, f"=G{excel_row}*H{excel_row}", number_format)
            worksheet.write_formula(
                offset,
                10,
                (
                    f"=IFERROR(J{excel_row}/SUMIF($A${first_excel_row}:$A${last_excel_row},"
                    f"A{excel_row},$J${first_excel_row}:$J${last_excel_row}),0)"
                ),
                percent_format,
            )
            worksheet.write_formula(
                offset,
                11,
                f"=IFERROR(J{excel_row}/SUM($J${first_excel_row}:$J${last_excel_row}),0)",
                percent_format,
            )
            worksheet.write(offset, 12, item["specification"], wrap_format)

        total_row = len(items) + 4
        worksheet.merge_range(total_row, 0, total_row, 7, "TOTAL GERAL", formats["total_label"])
        worksheet.write_formula(total_row, 8, f"=SUM(I{first_excel_row}:I{last_excel_row})", formats["total_number"])
        worksheet.write_formula(total_row, 9, f"=SUM(J{first_excel_row}:J{last_excel_row})", formats["total_number"])
        worksheet.write_number(total_row, 10, 1, formats["total_percent"])
        worksheet.write_number(total_row, 11, 1, formats["total_percent"])
        worksheet.write(total_row, 12, "", formats["total_label"])

    def _write_lot_summary_sheet(self, workbook, payload, formats):
        worksheet = workbook.add_worksheet("Resumo por Lote")
        metadata = payload["metadata"]
        lots = payload["lots"]

        worksheet.merge_range("A1:G1", "Resumo Consolidado por Lote", formats["title"])
        worksheet.merge_range(
            "A2:G2",
            f"Documento de referencia: {metadata['doc_nome'] or metadata['processo_assunto']}",
            formats["subtitle"],
        )
        headers = [
            "Lote",
            "Descricao",
            "Classe ABC",
            "Qtd. itens",
            "Valor estimado 12 meses (R$)",
            "% do total",
            "Observacoes",
        ]
        worksheet.write_row(3, 0, headers, formats["header"])
        worksheet.freeze_panes(4, 0)
        worksheet.set_column("A:A", 8)
        worksheet.set_column("B:B", 44)
        worksheet.set_column("C:C", 12)
        worksheet.set_column("D:D", 12)
        worksheet.set_column("E:F", 20)
        worksheet.set_column("G:G", 28)

        item_first_row = 5
        item_last_row = len(payload["items"]) + 4
        for offset, lot in enumerate(lots, start=4):
            excel_row = offset + 1
            alt = (offset - 4) % 2 == 0
            cell_format = formats["cell_alt"] if alt else formats["cell"]
            integer_format = formats["integer_alt"] if alt else formats["integer"]
            number_format = formats["number_alt"] if alt else formats["number"]
            wrap_format = formats["text_wrap_alt"] if alt else formats["text_wrap"]

            worksheet.write(offset, 0, lot["lot_code"], cell_format)
            worksheet.write(offset, 1, lot["description"], wrap_format)
            worksheet.write(offset, 2, lot["class_abc"], cell_format)
            worksheet.write_formula(
                offset,
                3,
                (
                    f"=COUNTIF('Itens da Licitacao'!$A${item_first_row}:$A${item_last_row},"
                    f"A{excel_row})"
                ),
                integer_format,
            )
            worksheet.write_formula(
                offset,
                4,
                (
                    f"=SUMIF('Itens da Licitacao'!$A${item_first_row}:$A${item_last_row},"
                    f"A{excel_row},'Itens da Licitacao'!$J${item_first_row}:$J${item_last_row})"
                ),
                number_format,
            )
            worksheet.write(offset, 6, lot.get("notes") or "", wrap_format)

        total_row = len(lots) + 4
        first_lot_row = 5
        last_lot_row = len(lots) + 4
        for row_index in range(4, total_row):
            excel_row = row_index + 1
            worksheet.write_formula(
                row_index,
                5,
                f"=IFERROR(E{excel_row}/$E${total_row + 1},0)",
                formats["percent_alt"] if (row_index - 4) % 2 == 0 else formats["percent"],
            )
        worksheet.merge_range(total_row, 0, total_row, 3, "TOTAL GERAL", formats["total_label"])
        worksheet.write_formula(total_row, 4, f"=SUM(E{first_lot_row}:E{last_lot_row})", formats["total_number"])
        worksheet.write_formula(total_row, 5, f"=SUM(F{first_lot_row}:F{last_lot_row})", formats["total_percent"])
        worksheet.write(total_row, 6, "", formats["total_label"])

        meta_row = total_row + 3
        meta_pairs = [
            ("Processo", metadata["processo_numero"]),
            ("Assunto", metadata["processo_assunto"]),
            ("Tipo do processo", metadata["process_type"]),
            ("Escopo", metadata["process_scope"]),
            ("Documento", metadata["doc_nome"]),
            ("Tipo do documento", metadata["doc_tipo"]),
            ("Template", metadata["documento_referencia"]),
        ]
        for label, value in meta_pairs:
            worksheet.write(meta_row, 0, label, formats["meta_label"])
            worksheet.merge_range(meta_row, 1, meta_row, 4, value or "-", formats["meta_value"])
            meta_row += 1

    def _write_schedule_sheet(self, workbook, payload, formats):
        worksheet = workbook.add_worksheet("Cronograma de Pedidos")
        worksheet.merge_range("A1:N1", "Cronograma de Pedidos / OF", formats["title"])
        worksheet.merge_range(
            "A2:N2",
            "Distribuicao sugerida dos pedidos ao longo do exercicio.",
            formats["subtitle"],
        )
        headers = ["Lote", "Descricao"] + [month_label for _month_key, month_label in self._MONTHS]
        worksheet.write_row(3, 0, headers, formats["header"])
        worksheet.freeze_panes(4, 0)
        worksheet.set_column("A:A", 8)
        worksheet.set_column("B:B", 34)
        worksheet.set_column("C:N", 14)

        for offset, row in enumerate(payload["schedule"], start=4):
            alt = (offset - 4) % 2 == 0
            text_format = formats["cell_alt"] if alt else formats["cell"]
            schedule_format = formats["schedule_mark"] if alt else formats["cell"]
            worksheet.write(offset, 0, row["lot_code"], text_format)
            worksheet.write(offset, 1, row["description"], formats["text_wrap_alt"] if alt else formats["text_wrap"])
            for column, (month_key, _month_label) in enumerate(self._MONTHS, start=2):
                worksheet.write(offset, column, row.get(month_key) or "", schedule_format)

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
