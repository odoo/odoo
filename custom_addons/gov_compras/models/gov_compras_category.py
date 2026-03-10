from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovComprasCategory(models.Model):
    _name = "gov.compras.category"
    _description = "Categoria de Itens de Compra"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = "name"
    _order = "code, name, id"

    name = fields.Char(string="Nome", required=True)
    code = fields.Char(
        string="Código de Classificação",
        required=True,
        readonly=True,
        copy=False,
        default="Novo",
        index=True,
    )
    sequence_number = fields.Integer(
        string="Sequência Interna",
        required=True,
        default=0,
        copy=False,
        help="Número sequencial usado para gerar o código hierárquico da categoria.",
    )
    parent_id = fields.Many2one(
        "gov.compras.category",
        string="Categoria Pai",
        index=True,
        ondelete="cascade",
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "gov.compras.category",
        "parent_id",
        string="Sub-Categorias",
    )
    item_ids = fields.One2many(
        "gov.compras.catalog.item",
        "category_id",
        string="Itens",
    )

    _code_unique = models.Constraint(
        "unique(code)",
        "Ja existe uma categoria com este código de classificação.",
    )

    @api.depends("name", "parent_id.name")
    def _compute_display_name(self):
        for category in self:
            if category.parent_id:
                category.display_name = f"{category.parent_id.display_name} / {category.name}"
            else:
                category.display_name = category.name

    @api.model
    def _next_sequence_number(self, parent_id=False):
        sibling = self.search(
            [("parent_id", "=", parent_id or False)],
            order="sequence_number desc, id desc",
            limit=1,
        )
        return (sibling.sequence_number or 0) + 1

    @api.model
    def _build_code(self, parent_id, sequence_number):
        segment = f"{int(sequence_number or 0):02d}"
        if not parent_id:
            return segment
        parent = self.browse(parent_id)
        return f"{parent.code}.{segment}"

    def _sync_code_with_children(self):
        for rec in self:
            new_code = rec._build_code(rec.parent_id.id, rec.sequence_number)
            if rec.code != new_code:
                super(GovComprasCategory, rec.with_context(skip_category_code_sync=True)).write(
                    {"code": new_code}
                )
            rec.child_ids._sync_code_with_children()

    @api.model_create_multi
    def create(self, vals_list):
        next_numbers = {}
        prepared_vals_list = []

        for vals in vals_list:
            prepared_vals = dict(vals)
            prepared_vals["name"] = (prepared_vals.get("name") or "").strip()
            parent_id = prepared_vals.get("parent_id") or False

            if not prepared_vals.get("sequence_number"):
                if parent_id not in next_numbers:
                    next_numbers[parent_id] = self._next_sequence_number(parent_id)
                prepared_vals["sequence_number"] = next_numbers[parent_id]
                next_numbers[parent_id] += 1

            code = (prepared_vals.get("code") or "").strip()
            if not code or code == "Novo":
                prepared_vals["code"] = self._build_code(
                    parent_id,
                    prepared_vals["sequence_number"],
                )
            else:
                prepared_vals["code"] = code

            prepared_vals_list.append(prepared_vals)

        return super().create(prepared_vals_list)

    def write(self, vals):
        if self.env.context.get("skip_category_code_sync"):
            return super().write(vals)

        base_vals = dict(vals)
        if "name" in base_vals:
            base_vals["name"] = (base_vals.get("name") or "").strip()
        if "code" in base_vals:
            base_vals.pop("code")

        if "parent_id" in base_vals and "sequence_number" not in base_vals:
            for rec in self:
                record_vals = dict(base_vals)
                new_parent_id = record_vals.get("parent_id") or False
                if rec.parent_id.id != new_parent_id:
                    record_vals["sequence_number"] = self._next_sequence_number(new_parent_id)
                super(GovComprasCategory, rec).write(record_vals)
                if rec.parent_id.id != new_parent_id or "sequence_number" in record_vals:
                    rec._sync_code_with_children()
            return True

        result = super().write(base_vals)
        if "parent_id" in base_vals or "sequence_number" in base_vals:
            self._sync_code_with_children()
        return result

    @api.constrains("name")
    def _check_name(self):
        for rec in self:
            if not (rec.name or "").strip():
                raise ValidationError("Nome da categoria nao pode ser vazio.")

    @api.constrains("sequence_number")
    def _check_sequence_number(self):
        for rec in self:
            if rec.sequence_number < 1:
                raise ValidationError("A sequência interna da categoria deve ser maior que zero.")

    @api.constrains("parent_id", "sequence_number")
    def _check_unique_sequence_per_parent(self):
        for rec in self:
            duplicates = self.search_count(
                [
                    ("id", "!=", rec.id),
                    ("parent_id", "=", rec.parent_id.id or False),
                    ("sequence_number", "=", rec.sequence_number),
                ]
            )
            if duplicates:
                raise ValidationError(
                    "Ja existe uma categoria com esta sequência interna dentro da mesma hierarquia."
                )
