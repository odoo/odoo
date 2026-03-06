import base64
import csv
import io
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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

        required_cols = ["Código", "Nome do Item", "Natureza da Despesa"]
        fieldnames = reader.fieldnames or []
        if not all(col in fieldnames for col in required_cols):
            raise UserError(f"O CSV deve conter as colunas exatas: {', '.join(required_cols)}")

        Item = self.env["gov.compras.catalog.item"]
        Category = self.env["gov.compras.category"]
        Uom = self.env["uom.uom"]
        AccountConfig = self.env["gov.account.config"]

        # Cache
        uom_cache = {}
        category_cache = {}
        natureza_cache = {}

        items_created = 0
        items_updated = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            code = (row.get("Código") or "").strip()
            name = (row.get("Nome do Item") or "").strip()
            natureza_str = (row.get("Natureza da Despesa") or "").strip()
            categoria_str = (row.get("Categoria") or "").strip()
            uom_str = (row.get("Unidade de Medida") or "UN").strip()
            descricao = (row.get("Descrição Técnica") or "").strip()

            if not code or not name or not natureza_str:
                errors.append(f"Linha {row_num}: Código, Nome ou Natureza vazios. Ignorado.")
                continue

            # 1. Resolver UoM
            if uom_str not in uom_cache:
                uom_cache[uom_str] = Uom.search([("name", "=ilike", uom_str)], limit=1)
                if not uom_cache[uom_str]:
                    # Tentar unidade padrão UN
                    uom_cache[uom_str] = Uom.search([("name", "=ilike", "unidade")], limit=1)

            uom_id = uom_cache[uom_str].id if uom_cache.get(uom_str) else False

            if not uom_id:
                errors.append(f"Linha {row_num}: Unidade de medida '{uom_str}' não encontrada.")
                continue

            # 2. Resolver Categoria Hierárquica
            category_id = False
            if categoria_str:
                parts = [p.strip() for p in categoria_str.split("/") if p.strip()]
                parent_id = False
                for part in parts:
                    cat_key = (part, parent_id)
                    if cat_key not in category_cache:
                        cat = Category.search([("name", "=ilike", part), ("parent_id", "=", parent_id)], limit=1)
                        if not cat:
                            cat = Category.create({"name": part, "parent_id": parent_id})
                        category_cache[cat_key] = cat.id
                    parent_id = category_cache[cat_key]
                category_id = parent_id

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
                "category_id": category_id,
                "uom_id": uom_id,
                "natureza_despesa_id": natureza_id.id,
                "descricao": descricao,
            }

            existing_item = Item.search([("code", "=", code)], limit=1)
            if existing_item:
                existing_item.write(item_vals)
                items_updated += 1
            else:
                item_vals["code"] = code
                # Nenhuma UG vinculada de cara (Fica só no Catálogo Geral)
                Item.create(item_vals)
                items_created += 1

        msg = f"Importação concluída.\nItens criados: {items_created}\nItens atualizados: {items_updated}"
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
