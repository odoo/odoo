import datetime
import logging
from ast import literal_eval
from collections import defaultdict
from typing import Any

from odoo import api, fields, models, modules, tools
from odoo.db.errors import PG_USER_FAULT_EXCEPTIONS
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import SQL

_logger = logging.getLogger("odoo.addons.product.merge")


def _can_commit() -> bool:
    return not (tools.config["test_enable"] or modules.module.current_test)


class ProductMergeLine(models.TransientModel):
    _name = "product.merge.line"
    _description = "Merge Product Line"
    _order = "min_id asc"

    wizard_id = fields.Many2one(comodel_name="product.merge.wizard")
    min_id = fields.Integer(string="MinID")
    aggr_ids = fields.Char(
        string="Ids",
        required=True,
    )


class ProductMergeWizard(models.TransientModel):
    _name = "product.merge.wizard"
    _inherit = ["mixin.merge"]
    _description = "Merge Products Wizard"

    # Products carry more cross-model side effects to reconcile per merge
    # (variants, attribute lines, pricelist rules) than a plain partner merge,
    # so the batch is kept small; re-open the wizard to merge more.
    _MAX_MERGE_SIZE = 3

    _GROUPBY_ALLOWED_FIELDS = frozenset(
        {"name", "default_code", "barcode", "categ_id", "type", "uom_id"}
    )
    _VARIANT_GROUPBY_FIELDS = frozenset({"barcode"})
    _CASE_INSENSITIVE_GROUPBY_FIELDS = frozenset({"name", "default_code", "barcode"})

    @api.model
    def default_get(self, fields: list[str]) -> dict[str, Any]:
        res = super().default_get(fields)
        active_ids = self.env.context.get("active_ids")
        active_model = self.env.context.get("active_model")
        if (
            active_model not in ("product.template", "product.product")
            or not active_ids
        ):
            return res

        if active_model == "product.product":
            templates = (
                self.env["product.product"]
                .browse(active_ids)
                .with_context(active_test=False)
                .product_tmpl_id
            )
        else:
            templates = self.env["product.template"].browse(active_ids)

        if "state" in fields:
            res["state"] = "selection"
        if "product_tmpl_ids" in fields:
            res["product_tmpl_ids"] = [Command.set(templates.ids)]
        if "dst_product_tmpl_id" in fields and templates:
            res["dst_product_tmpl_id"] = self._get_ordered_templates(templates.ids)[
                -1
            ].id
        return res

    group_by_name = fields.Boolean(string="Name")
    group_by_default_code = fields.Boolean(string="Internal Reference")
    group_by_barcode = fields.Boolean(string="Barcode")
    group_by_categ_id = fields.Boolean(string="Product Category")
    group_by_type = fields.Boolean(string="Product Type")
    group_by_uom_id = fields.Boolean(string="Unit")

    state = fields.Selection(
        selection=[
            ("option", "Option"),
            ("selection", "Selection"),
            ("finished", "Finished"),
        ],
        default="option",
        readonly=True,
        required=True,
    )

    number_group = fields.Integer(
        string="Group of Products",
        readonly=True,
    )
    maximum_group = fields.Integer(
        string="Maximum of Group of Products",
        default=100,
    )
    current_line_id = fields.Many2one(comodel_name="product.merge.line")
    line_ids = fields.One2many(
        comodel_name="product.merge.line",
        inverse_name="wizard_id",
        string="Lines",
    )
    product_tmpl_ids = fields.Many2many(
        comodel_name="product.template",
        string="Products",
        context={"active_test": False},
    )
    dst_product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Destination Product",
    )

    exclude_journal_item = fields.Boolean(
        string="Journal Items associated to the product"
    )

    def _get_merge_tables_excluded(self, model: str) -> set[str]:
        tables = super()._get_merge_tables_excluded(model)
        if model == "product.template":
            return tables | self._get_excluded_template_tables()
        if model == "product.product":
            return tables | self._get_excluded_variant_tables()
        return tables

    def _get_excluded_template_tables(self) -> set[str]:
        return {
            "product_product",
            "product_attribute_product_template_rel",
            "product_template_attribute_line",
            "product_template_attribute_value",
            "product_template_attribute_exclusion",
        }

    def _get_excluded_variant_tables(self) -> set[str]:
        return {"product_variant_combination"}

    def _get_fields_summable(self) -> list[str]:
        return []

    def _get_fields_summable_variant(self) -> list[str]:
        return []

    def _get_fields_excluded_value(self) -> tuple[str, ...]:
        return ("company_id",)

    def _get_fields_deferred_variant(self) -> tuple[str, ...]:
        return ("barcode",)

    def _get_ordered_templates(self, template_ids: list[int]) -> models.BaseModel:
        return (
            self.env["product.template"]
            .browse(template_ids)
            .sorted(
                key=lambda template: (
                    not template.active,
                    (template.create_date or datetime.datetime(1970, 1, 1)),
                ),
                reverse=True,
            )
        )

    def _check_mergeable(
        self, src_templates: models.BaseModel, dst_template: models.BaseModel
    ) -> None:
        templates = src_templates + dst_template

        if len(set(templates.mapped("type"))) > 1:
            raise UserError(
                self.env._(
                    "You cannot merge products of different types (%(types)s).",
                    types=", ".join(sorted(set(templates.mapped("type")))),
                )
            )

        if len(templates.uom_id) > 1:
            raise UserError(
                self.env._(
                    "You cannot merge products measured in different units "
                    "(%(units)s). Every quantity already recorded against the "
                    "source products would silently change meaning.",
                    units=", ".join(sorted(templates.uom_id.mapped("name"))),
                )
            )

        if dst_template.company_id:
            other_company = src_templates.filtered(
                lambda template: template.company_id != dst_template.company_id
            )
            if other_company:
                raise UserError(
                    self.env._(
                        "The destination product belongs to %(company)s while "
                        "%(products)s do not. Merge into the product shared "
                        "between companies instead, or the documents of the "
                        "other companies would end up pointing at a product "
                        "they cannot use.",
                        company=dst_template.company_id.display_name,
                        products=", ".join(other_company.mapped("display_name")),
                    )
                )

    def _get_variant_pairs(
        self, src_template: models.BaseModel, dst_template: models.BaseModel
    ) -> dict[models.BaseModel, models.BaseModel]:

        def combination(variant: models.BaseModel) -> frozenset[int]:
            values = variant.product_template_attribute_value_ids
            return frozenset(values.product_attribute_value_id.ids)

        dst_variants = dst_template.with_context(active_test=False).product_variant_ids
        dst_by_combination = {combination(variant): variant for variant in dst_variants}

        pairs = {}
        for variant in src_template.with_context(active_test=False).product_variant_ids:
            counterpart = dst_by_combination.get(combination(variant))
            if not counterpart:
                raise UserError(
                    self.env._(
                        "%(product)s has no counterpart among the variants of "
                        "%(destination)s. Products can only be merged when "
                        "every variant of the source matches one of the "
                        "destination on the same attribute values.",
                        product=variant.display_name,
                        destination=dst_template.display_name,
                    )
                )
            pairs[variant] = counterpart
        return pairs

    @api.model
    def _update_foreign_keys(
        self, src_templates: models.BaseModel, dst_template: models.BaseModel
    ) -> None:
        self._update_foreign_keys_generic(
            "product.template", src_templates, dst_template
        )

    @api.model
    def _update_reference_fields(
        self, src_templates: models.BaseModel, dst_template: models.BaseModel
    ) -> None:
        self._update_reference_fields_generic(
            "product.template", src_templates, dst_template
        )

    @api.model
    def _update_values(
        self, src_templates: models.BaseModel, dst_template: models.BaseModel
    ) -> None:
        self._update_values_generic(
            src_templates,
            dst_template,
            summable_fields=self._get_fields_summable(),
            excluded_fields=self._get_fields_excluded_value(),
        )

    @api.model
    def _update_variant_foreign_keys(
        self, src_variants: models.BaseModel, dst_variant: models.BaseModel
    ) -> None:
        self._update_foreign_keys_generic("product.product", src_variants, dst_variant)

    @api.model
    def _update_variant_reference_fields(
        self, src_variants: models.BaseModel, dst_variant: models.BaseModel
    ) -> None:
        self._update_reference_fields_generic(
            "product.product", src_variants, dst_variant
        )

    @api.model
    def _update_variant_values(
        self, src_variants: models.BaseModel, dst_variant: models.BaseModel
    ) -> dict[str, Any]:
        return self._update_values_generic(
            src_variants,
            dst_variant,
            summable_fields=self._get_fields_summable_variant(),
            deferred_fields=self._get_fields_deferred_variant(),
            excluded_fields=self._get_fields_excluded_value(),
        )

    def _merge(
        self,
        product_tmpl_ids: list[int],
        dst_template: models.BaseModel | None = None,
    ) -> None:
        templates = self.env["product.template"].browse(product_tmpl_ids).exists()
        if len(templates) < 2:
            return

        if len(templates) > self._MAX_MERGE_SIZE:
            raise UserError(
                self.env._(
                    "For safety reasons, you cannot merge more than %(maximum)s "
                    "products together. You can re-open the wizard several "
                    "times if needed.",
                    maximum=self._MAX_MERGE_SIZE,
                )
            )

        if dst_template and dst_template in templates:
            src_templates = templates - dst_template
        else:
            ordered_templates = self._get_ordered_templates(templates.ids)
            dst_template = ordered_templates[-1]
            src_templates = ordered_templates[:-1]
        _logger.info("dst_template: %s", dst_template.id)

        self._check_mergeable(src_templates, dst_template)

        src_variants_by_dst = defaultdict(lambda: self.env["product.product"])
        for src_template in src_templates:
            pairs = self._get_variant_pairs(src_template, dst_template)
            for src_variant, dst_variant in pairs.items():
                src_variants_by_dst[dst_variant] |= src_variant

        deferred_variant_values = {}
        for dst_variant, src_variants in src_variants_by_dst.items():
            self._update_variant_foreign_keys(src_variants, dst_variant)
            self._update_variant_reference_fields(src_variants, dst_variant)
            deferred_variant_values[dst_variant] = self._update_variant_values(
                src_variants, dst_variant
            )

        self._update_foreign_keys(src_templates, dst_template)
        self._update_reference_fields(src_templates, dst_template)
        self._update_values(src_templates, dst_template)

        self._log_merge_operation(src_templates, dst_template)

        src_variants = self.env["product.product"].union(*src_variants_by_dst.values())
        src_variants.sudo().unlink()
        src_templates.exists().sudo().unlink()

        for dst_variant, values in deferred_variant_values.items():
            if values:
                dst_variant.write(values)

    def _log_merge_operation(
        self, src_templates: models.BaseModel, dst_template: models.BaseModel
    ) -> None:
        _logger.info(
            "(uid = %s) merged the products %r into %s",
            self.env.uid,
            src_templates.ids,
            dst_template.id,
        )
        dst_template.message_post(
            body=self.env._(
                "Merged with the following products: %s",
                [
                    self.env._(
                        "%(product)s (ID %(id)s)",
                        product=template.display_name,
                        id=template.id,
                    )
                    for template in src_templates
                ],
            )
        )

    @api.model
    def _generate_query(self, fields: list[str], maximum_group: int = 100) -> SQL:
        template = SQL.identifier("template")
        variant = SQL.identifier("variant")

        group_expressions = []
        filters = []
        for field in fields:
            if field not in self._GROUPBY_ALLOWED_FIELDS:
                raise ValueError(f"Field {field!r} is not allowed in merge grouping")
            alias = variant if field in self._VARIANT_GROUPBY_FIELDS else template
            column = SQL("%s.%s", alias, SQL.identifier(field))
            if field == "name":
                expression = SQL(
                    "lower(COALESCE(%s ->> %s, %s ->> 'en_US'))",
                    column,
                    self.env.lang or "en_US",
                    column,
                )
            elif field in self._CASE_INSENSITIVE_GROUPBY_FIELDS:
                expression = SQL("lower(%s)", column)
            else:
                expression = column
            group_expressions.append(expression)
            filters.append(SQL("%s IS NOT NULL", expression))

        parts = [
            SQL("SELECT min(%s.id), array_agg(DISTINCT %s.id)", template, template),
            SQL("FROM product_template AS %s", template),
        ]
        if not self._VARIANT_GROUPBY_FIELDS.isdisjoint(fields):
            parts.append(
                SQL(
                    "JOIN product_product AS %s ON %s.product_tmpl_id = %s.id",
                    variant,
                    variant,
                    template,
                )
            )
        if filters:
            parts.append(SQL("WHERE %s", SQL(" AND ").join(filters)))
        parts.extend(
            [
                SQL("GROUP BY %s", SQL(", ").join(group_expressions)),
                SQL("HAVING COUNT(DISTINCT %s.id) >= 2", template),
                SQL("ORDER BY min(%s.id)", template),
            ]
        )
        if maximum_group:
            parts.append(SQL("LIMIT %s", maximum_group))

        return SQL(" ").join(parts)

    def _get_selected_groupby(self) -> list[str]:
        group_by_prefix = "group_by_"
        groups = [
            field_name.removeprefix(group_by_prefix)
            for field_name in self._fields
            if field_name.startswith(group_by_prefix) and self[field_name]
        ]

        if not groups:
            raise UserError(
                self.env._("You have to specify a filter for your selection.")
            )

        return groups

    def _get_exclusion_models(self) -> dict[str, str]:
        model_mapping = {}
        if "account.move.line" in self.env and self.exclude_journal_item:
            model_mapping["account.move.line"] = "product_id"
        return model_mapping

    @api.model
    def _get_excluded_templates(
        self, template_ids: list[int], models: dict[str, str]
    ) -> set[int]:
        templates = (
            self.env["product.template"]
            .browse(template_ids)
            .with_context(active_test=False)
        )
        return {
            template.id
            for template in templates
            if any(
                self.env[model].search_count(
                    [(field, "in", template.product_variant_ids.ids)]
                )
                for model, field in models.items()
            )
        }

    def _create_merge_lines_from_query(self, query: SQL) -> None:
        self.check_singleton()
        model_mapping = self._get_exclusion_models()

        self.env.flush_all()
        self.env.cr.execute(query)  # noqa: E8501  built by _generate_query

        groups = self.env.cr.fetchall()
        all_ids = [tmpl_id for _, aggr_ids in groups for tmpl_id in aggr_ids]
        accessible = self.env["product.template"].search([("id", "in", all_ids)])
        accessible_set = set(accessible.ids)

        counter = 0
        for min_id, aggr_ids in groups:
            template_ids = [
                tmpl_id for tmpl_id in aggr_ids if tmpl_id in accessible_set
            ]
            if model_mapping:
                excluded = self._get_excluded_templates(template_ids, model_mapping)
                template_ids = [
                    tmpl_id for tmpl_id in template_ids if tmpl_id not in excluded
                ]
            if len(template_ids) < 2:
                continue

            self.env["product.merge.line"].create(
                {
                    "wizard_id": self.id,
                    "min_id": min_id,
                    "aggr_ids": template_ids,
                }
            )
            counter += 1

        self.write({"state": "selection", "number_group": counter})

        _logger.info("counter: %s", counter)

    def _action_next_screen(self) -> dict[str, Any]:
        self.env.invalidate_all()
        values = {}
        if self.line_ids:
            current_line = self.line_ids[0]
            current_template_ids = literal_eval(current_line.aggr_ids)
            values.update(
                {
                    "current_line_id": current_line.id,
                    "product_tmpl_ids": [Command.set(current_template_ids)],
                    "dst_product_tmpl_id": self._get_ordered_templates(
                        current_template_ids
                    )[-1].id,
                    "state": "selection",
                }
            )
        else:
            values.update(
                {
                    "current_line_id": False,
                    "product_tmpl_ids": [],
                    "state": "finished",
                }
            )

        self.write(values)

        return self._action_reopen()

    def _action_reopen(self) -> dict[str, Any]:
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_skip(self) -> dict[str, Any]:
        if self.current_line_id:
            self.current_line_id.unlink()
        return self._action_next_screen()

    def action_merge(self) -> dict[str, Any]:
        self.check_singleton()
        if not self.product_tmpl_ids:
            self.write({"state": "finished"})
            return self._action_reopen()

        if len(self.product_tmpl_ids) < 2:
            raise UserError(
                self.env._("Select at least two products to merge them together.")
            )

        self._merge(self.product_tmpl_ids.ids, self.dst_product_tmpl_id)

        if self.current_line_id:
            self.current_line_id.unlink()

        return self._action_next_screen()

    def action_start_manual_process(self) -> dict[str, Any]:
        self.check_singleton()
        groups = self._get_selected_groupby()
        query = self._generate_query(groups, self.maximum_group)
        self._create_merge_lines_from_query(query)
        return self._action_next_screen()

    def action_start_automatic_process(self) -> dict[str, Any]:
        self.check_singleton()
        self.action_start_manual_process()
        self.env.invalidate_all()

        for line in self.line_ids:
            template_ids = literal_eval(line.aggr_ids)
            try:
                with self.env.cr.savepoint():
                    self._merge(template_ids)
            except (UserError, ValidationError, *PG_USER_FAULT_EXCEPTIONS) as error:
                _logger.warning(
                    "Skipping the merge of products %s: %s", template_ids, error
                )
                continue
            line.unlink()
            if _can_commit():
                self.env.cr.commit()

        return self._action_next_screen()
