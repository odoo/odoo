import base64
import csv
import io

from odoo import fields, models
from odoo.exceptions import UserError


class GovComprasImportWizard(models.TransientModel):
    _name = "gov.compras.import.wizard"
    _description = "Assistente de Importação do Catálogo (Comprasnet)"

    file = fields.Binary(string="Arquivo CSV", required=True)
    filename = fields.Char(string="Nome do Arquivo")
    delimiter = fields.Selection(
        [(";", "Ponto e Vírgula (;)"), (",", "Vírgula (,)")],
        string="Separador",
        default=";",
        required=True,
    )

    def _get_row_value(self, row, *column_names):
        for column_name in column_names:
            if column_name in row:
                return (row.get(column_name) or "").strip()
        return ""

    def _has_any_column(self, fieldnames, *column_names):
        return any(column_name in fieldnames for column_name in column_names)

    def _resolve_uom(self, uom_name, uom_cache):
        normalized_name = (uom_name or "").strip()
        if normalized_name not in uom_cache:
            Uom = self.env["uom.uom"]
            default_uom = self.env.ref("uom.product_uom_unit", raise_if_not_found=False)
            uom = Uom.search([("name", "=ilike", normalized_name)], limit=1) if normalized_name else False
            if not uom:
                uom = Uom.search([("name", "=ilike", "unidade")], limit=1) or default_uom
            uom_cache[normalized_name] = uom
        return uom_cache.get(normalized_name)

    def _resolve_category(self, category_value, subcategory_value, category_cache):
        Category = self.env["gov.compras.category"]
        raw_parts = []

        if category_value:
            raw_parts.extend(category_value.split("/"))
        if subcategory_value:
            raw_parts.extend(subcategory_value.split("/"))

        parent_id = False
        category_id = False
        created_count = 0

        for part in [part.strip() for part in raw_parts if part.strip()]:
            cache_key = (part.casefold(), parent_id)
            if cache_key not in category_cache:
                category = Category.search(
                    [("name", "=ilike", part), ("parent_id", "=", parent_id)],
                    limit=1,
                )
                if not category:
                    category = Category.create({"name": part, "parent_id": parent_id})
                    created_count += 1
                category_cache[cache_key] = category.id
            parent_id = category_cache[cache_key]
            category_id = parent_id

        return category_id, created_count

    def _find_existing_item(self, external_code):
        Item = self.env["gov.compras.catalog.item"]
        item = Item.search([("external_code", "=", external_code)], limit=1)
        if item:
            return item

        return Item.search(
            [("external_code", "=", False), ("code", "=", external_code)],
            limit=1,
        )

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError("Por favor, envie um arquivo.")

        try:
            file_content = base64.b64decode(self.file).decode("utf-8-sig")
            reader = csv.DictReader(
                io.StringIO(file_content), delimiter=self.delimiter
            )
        except Exception as e:
            raise UserError(f"Erro ao ler o arquivo CSV. Verifique o formato e codificação (UTF-8).\nDetalhes: {e}")

        fieldnames = reader.fieldnames or []
        missing_labels = []
        if not self._has_any_column(fieldnames, "Código", "Codigo", "ID", "Id", "ID Externo", "Código Externo", "Codigo Externo"):
            missing_labels.append("Código/ID")
        if not self._has_any_column(fieldnames, "Nome do Item", "Nome Item", "Item"):
            missing_labels.append("Nome do Item")
        if not self._has_any_column(fieldnames, "Natureza da Despesa"):
            missing_labels.append("Natureza da Despesa")
        if missing_labels:
            raise UserError(
                "O CSV deve conter as colunas obrigatórias: "
                + ", ".join(missing_labels)
            )

        Item = self.env["gov.compras.catalog.item"]
        AccountConfig = self.env["gov.account.config"]

        # Cache
        uom_cache = {}
        category_cache = {}
        natureza_cache = {}

        items_created = 0
        items_updated = 0
        categories_created = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            external_code = self._get_row_value(
                row,
                "Código",
                "Codigo",
                "ID",
                "Id",
                "ID Externo",
                "Código Externo",
                "Codigo Externo",
            )
            name = self._get_row_value(row, "Nome do Item", "Nome Item", "Item")
            natureza_str = self._get_row_value(row, "Natureza da Despesa")
            categoria_str = self._get_row_value(row, "Categoria")
            subcategoria_str = self._get_row_value(row, "Subcategoria", "Sub-Categoria")
            uom_str = self._get_row_value(row, "Unidade de Medida", "Unidade") or "UN"
            descricao = self._get_row_value(row, "Descrição Técnica", "Descricao Tecnica", "Descrição", "Descricao")

            if not external_code or not name or not natureza_str:
                errors.append(f"Linha {row_num}: Código, Nome ou Natureza vazios. Ignorado.")
                continue

            # 1. Resolver UoM
            uom = self._resolve_uom(uom_str, uom_cache)
            uom_id = uom.id if uom else False

            if not uom_id:
                errors.append(f"Linha {row_num}: Unidade de medida '{uom_str}' nao encontrada.")
                continue

            # 2. Resolver Categoria Hierárquica
            category_id = False
            if categoria_str or subcategoria_str:
                category_id, created_count = self._resolve_category(
                    categoria_str,
                    subcategoria_str,
                    category_cache,
                )
                categories_created += created_count

            # 3. Resolver Natureza da Despesa (Precisa existir no Mapeamento Contábil)
            if natureza_str not in natureza_cache:
                natureza = AccountConfig.get_config(natureza_str)
                natureza_cache[natureza_str] = natureza

            natureza_id = natureza_cache[natureza_str]

            if not natureza_id:
                errors.append(f"Linha {row_num}: Natureza da Despesa '{natureza_str}' não encontrada no Mapeamento Contábil. Item ignorado.")
                continue

            # 4. Criar ou Atualizar Item (Catálogo Geral, ug_ids=False init)
            item_vals = {
                "name": name,
                "external_code": external_code,
                "category_id": category_id,
                "uom_id": uom_id,
                "natureza_despesa_id": natureza_id.id,
                "descricao": descricao,
            }

            existing_item = self._find_existing_item(external_code)
            if existing_item:
                existing_item.write(item_vals)
                items_updated += 1
            else:
                # Nenhuma UG vinculada de cara (Fica só no Catálogo Geral)
                Item.create(item_vals)
                items_created += 1

        msg = (
            "Importação concluída.\n"
            f"Itens criados: {items_created}\n"
            f"Itens atualizados: {items_updated}\n"
            f"Categorias/Subcategorias criadas: {categories_created}"
        )
        if errors:
            msg += "\n\nAvisos/Erros:\n" + "\n".join(e for e in errors[:20])
            if len(errors) > 20:
                msg += f"\n... e mais {len(errors) - 20} erros."

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Resultado da Importação",
                "message": msg,
                "type": "warning" if errors else "success",
                "sticky": True if errors else False,
            }
        }
