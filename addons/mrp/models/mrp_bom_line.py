from collections import defaultdict
from itertools import starmap

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import formatLang

_debug = DebugLog(__name__)


class MrpBomLine(models.Model):
    _name = "mrp.bom.line"
    _inherit = ["mixin.bom.component"]
    _description = "Bill of Material Line"

    _bom_child_field = "bom_line_ids"

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Component",
    )
    product_tmpl_id = fields.Many2one(  # noqa: E8529  One2many inverse of product.template.bom_line_ids
        comodel_name="product.template",
        related="product_id.product_tmpl_id",
        string="Product Template",
        store=True,
        index=True,
    )
    sequence = fields.Integer(default=1)
    parent_product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        related="bom_id.product_tmpl_id",
        string="Parent Product Template",
    )
    operation_id = fields.Many2one(
        comodel_name="mrp.routing.workcenter",
        string="Consumed in Operation",
        help="The operation where the components are consumed, or the finished products created.",
    )
    child_bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="Sub BoM",
        compute="_compute_child_bom_id",
    )
    child_line_ids = fields.One2many(
        comodel_name="mrp.bom.line",
        string="BOM lines of the referred bom",
        compute="_compute_child_line_ids",
    )
    attachments_count = fields.Integer(compute="_compute_attachments_count")
    tracking = fields.Selection(related="product_id.tracking")

    @api.depends("product_id", "bom_id.company_id", "bom_id.picking_type_id")
    def _compute_child_bom_id(self):
        Bom = self.env["mrp.bom"]
        for (company, picking_type), lines in self.grouped(
            lambda line: (line.bom_id.company_id, line.bom_id.picking_type_id)
        ).items():
            bom_by_product = Bom._get_bom_by_product(
                lines.product_id, picking_type=picking_type, company_id=company.id
            )
            for line in lines:
                line.child_bom_id = bom_by_product.get(line.product_id, False)

    @api.depends("product_id")
    def _compute_attachments_count(self):
        counts_by_product = {}
        counts_by_template = {}
        for res_model, counts in (
            ("product.product", counts_by_product),
            ("product.template", counts_by_template),
        ):
            res_ids = (
                self.product_id.ids
                if res_model == "product.product"
                else self.product_tmpl_id.ids
            )
            if not res_ids:
                continue
            counts.update(
                dict(
                    self.env["document.document"]._read_group(  # noqa: E8507 - one query per attachment model (product, template)
                        [
                            ("attached_on_mrp", "=", "bom"),
                            ("active", "=", True),
                            ("res_model", "=", res_model),
                            ("res_id", "in", res_ids),
                        ],
                        ["res_id"],
                        ["__count"],
                    )
                )
            )
        for line in self:
            line.attachments_count = counts_by_product.get(
                line.product_id.id, 0
            ) + counts_by_template.get(line.product_tmpl_id.id, 0)

    @api.depends("child_bom_id")
    def _compute_child_line_ids(self):
        for line in self:
            line.child_line_ids = line.child_bom_id.bom_line_ids

    def _get_uom_mismatch_message(self):
        return _(
            "The component %(product)s is used in %(unit)s, which does"
            " not measure the same thing as its own unit"
            " %(product_unit)s.",
            product=self.product_id.display_name,
            unit=self.product_uom_id.display_name,
            product_unit=self.product_id.uom_id.display_name,
        )

    _CHATTER_TRACKED_FIELDS = (
        "product_id",
        "product_qty",
        "product_uom_id",
        "operation_id",
        "bom_product_template_attribute_value_ids",
    )

    _OUTDATING_FIELDS = ("product_id", "product_qty", "product_uom_id")

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        _debug.lifecycle("create", lines=lines, boms=lines.bom_id)
        lines.bom_id.with_context(
            skip_bom_outdated_unmark=True
        )._update_outdated_bom_in_productions()
        if not self._is_chatter_muted():
            for bom, added in lines.grouped("bom_id").items():
                bom.message_post(
                    body=Markup("{}<ul>{}</ul>").format(
                        self.env._("Components added:"),
                        Markup("").join(
                            Markup("<li><b>{}</b> — {}: {} {}</li>").format(
                                line.product_id.display_name,
                                line._get_chatter_label("product_qty"),
                                formatLang(
                                    self.env, line.product_qty, dp="Product Unit"
                                ),
                                line.product_uom_id.display_name,
                            )
                            for line in added
                        ),
                    ),
                    subtype_xmlid="mail.mt_note",
                )
        return lines

    def write(self, vals):
        if any(field_name in vals for field_name in self._OUTDATING_FIELDS):
            self.bom_id.with_context(
                skip_bom_outdated_unmark=True
            )._update_outdated_bom_in_productions()

        tracked = [name for name in self._CHATTER_TRACKED_FIELDS if name in vals]
        _debug.lifecycle("write", lines=self, fields=list(vals), tracked=len(tracked))
        if not tracked or self._is_chatter_muted():
            return super().write(vals)

        before = {
            line.id: (line.product_id.display_name, line._get_chatter_values(tracked))
            for line in self
        }
        result = super().write(vals)

        labels = {name: self._get_chatter_label(name) for name in tracked}
        changes_by_bom = defaultdict(list)
        for line in self:
            component, old_values = before[line.id]
            new_values = line._get_chatter_values(tracked)
            changes = [
                (labels[name], old_values[name], new_values[name])
                for name in tracked
                if old_values[name] != new_values[name]
            ]
            if changes:
                changes_by_bom[line.bom_id].append((component, changes))

        _debug.pipeline("bom_line_changes_posted", lines=self, boms=len(changes_by_bom))
        for bom, entries in changes_by_bom.items():
            bom.message_post(
                body=Markup("{}<ul>{}</ul>").format(
                    self.env._("Components updated:"),
                    Markup("").join(
                        Markup("<li><b>{}</b><ul>{}</ul></li>").format(
                            component,
                            Markup("").join(
                                starmap(Markup("<li>{}: {} → {}</li>").format, changes)
                            ),
                        )
                        for component, changes in entries
                    ),
                ),
                subtype_xmlid="mail.mt_note",
            )
        return result

    def unlink(self):
        boms = self.bom_id
        _debug.lifecycle("unlink", lines=self, boms=boms)
        result = self._unlink_and_notify_boms()
        boms.with_context(
            skip_bom_outdated_unmark=True
        )._update_outdated_bom_in_productions()
        return result

    def _unlink_and_notify_boms(self):
        if self._is_chatter_muted():
            return super().unlink()

        for bom, lines in self.grouped("bom_id").items():
            bom.message_post(
                body=Markup("{}<ul>{}</ul>").format(
                    self.env._("Components removed:"),
                    Markup("").join(
                        Markup("<li><b>{}</b> — {}: {} {}</li>").format(
                            line.product_id.display_name,
                            line._get_chatter_label("product_qty"),
                            formatLang(self.env, line.product_qty, dp="Product Unit"),
                            line.product_uom_id.display_name,
                        )
                        for line in lines
                    ),
                ),
                subtype_xmlid="mail.mt_note",
            )
        return super().unlink()

    def _is_chatter_muted(self):
        return bool(
            self.env.context.get("tracking_disable")
            or self.env.context.get("mail_notrack")
        )

    def _get_chatter_label(self, field_name):
        return self._fields[field_name].get_description(
            self.env, attributes=["string"]
        )["string"]

    def _get_chatter_values(self, field_names):
        self.check_singleton()
        return {name: self._get_chatter_value(name) for name in field_names}

    def _get_chatter_value(self, field_name):
        self.check_singleton()
        field = self._fields[field_name]
        value = self[field_name]
        if field.relational:
            return ", ".join(value.mapped("display_name")) or self.env._("(none)")
        if field.type == "float":
            return formatLang(self.env, value, dp="Product Unit")
        if field.type == "selection":
            return dict(field._description_selection(self.env)).get(value, value)
        return str(value)

    def action_see_attachments(self):
        self.check_singleton()
        domain = [
            "&",
            ("attached_on_mrp", "=", "bom"),
            "|",
            "&",
            ("res_model", "=", "product.product"),
            ("res_id", "=", self.product_id.id),
            "&",
            ("res_model", "=", "product.template"),
            ("res_id", "=", self.product_id.product_tmpl_id.id),
        ]
        counts = dict(
            self.env["document.document"]._read_group(
                domain, ["res_model"], ["__count"]
            )
        )
        nbr_product_attach = counts.get("product.product", 0)
        nbr_template_attach = counts.get("product.template", 0)
        context = {
            "default_res_model": "product.product",
            "default_res_id": self.product_id.id,
            "default_company_id": self.company_id.id,
            "attached_on_bom": True,
            "search_default_context_variant": not (
                nbr_product_attach == 0 and nbr_template_attach > 0
            )
            if self.env.user.has_group("product.group_product_variant")
            else False,
        }

        return {
            "name": _("Attachments"),
            "domain": domain,
            "res_model": "document.document",
            "type": "ir.actions.act_window",
            "view_mode": "kanban,list,form",
            "target": "current",
            "help": _("""<p class="o_view_nocontent_smiling_face">
                        Upload files to your product
                    </p><p>
                        Use this feature to store any files, like drawings or specifications.
                    </p>"""),
            "limit": 80,
            "context": context,
            "views": [
                (
                    self.env.ref(
                        "document_product.view_documents_document_product_kanban"
                    ).id,
                    "kanban",
                ),
                (
                    self.env.ref(
                        "document_product.view_documents_document_product_list"
                    ).id,
                    "list",
                ),
                (
                    self.env.ref(
                        "document_product.view_documents_document_product_form"
                    ).id,
                    "form",
                ),
            ],
            "search_view_id": self.env.ref(
                "document_product.view_documents_document_product_search"
            ).ids,
        }

    def _prepare_action_still_used_warning(self):
        products = self.product_id
        if not products:
            return None
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._(
                    "Note that product(s): '%s' is/are still linked to active Bill of "
                    "Materials, which means that the product can still be used on "
                    "it/them.",
                    products.mapped("display_name"),
                ),
                "type": "warning",
                "sticky": True,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _get_exploded_kit_quantity(self, bom, line_quantity, ancestors):
        self.check_singleton()
        if self.product_id.id in ancestors:
            _debug.logic(
                "bom_cycle_detected",
                bom_line=self.id,
                bom=bom.id,
                product=self.product_id.id,
                ancestors=len(ancestors),
            )
            raise ValidationError(
                _(
                    "The current configuration is incorrect because it would "
                    "create a cycle between these products: %s.",
                    self.product_id.display_name,
                )
            )
        return self.product_uom_id._get_quantity_in_unit(
            line_quantity / bom.product_qty, bom.product_uom_id, round=False
        )

    def _prepare_bom_done_values(self, quantity, product, original_quantity, boms_done):
        return {
            "qty": quantity,
            "product": product,
            "original_qty": original_quantity,
            "parent_line": self,
        }

    def _prepare_line_done_values(
        self, quantity, product, original_quantity, parent_line, boms_done
    ):
        return {
            "qty": quantity,
            "product": product,
            "original_qty": original_quantity,
            "parent_line": parent_line,
        }
