# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import _, Command, api, fields, models
from odoo.addons.web_studio.wizard.studio_export_wizard import FIELDS_TO_EXPORT
from odoo.osv import expression

# List of preset models to export when the preset action is triggered.
# This list may include specific defaults for each model.
PRESET_MODELS_DEFAULTS = [
    ("appointment.resource", {"updatable": False}),
    ("res.partner", {"domain": "[('user_ids', '=', False)]", "is_demo_data": True, "updatable": False}),
    ("hr.employee", {"is_demo_data": True, "updatable": False}),
    ("hr.applicant", {"is_demo_data": True, "updatable": False}),
    ("hr.candidate", {"is_demo_data": True, "updatable": False}),
    ("hr.department", {"is_demo_data": True, "updatable": False}),
    ("hr.job", {"is_demo_data": True, "updatable": False}),
    ("hr.recruitment.stage", {"updatable": False}),
    ("product.public.category", {"updatable": False}),
    ("project.task.type", {"updatable": False}),
    ("documents.document", {"domain": "[('type', '=', 'folder')]", "updatable": False}),
    ("product.category", {"updatable": False}),
    ("worksheet.template", {}),
    ("account.analytic.plan", {"is_demo_data": True, "updatable": False}),
    ("account.analytic.account", {"is_demo_data": True, "updatable": False}),
    ("appointment.type", {"is_demo_data": True, "updatable": False}),
    ("project.project", {"updatable": False}),
    ("uom.category", {"updatable": False}),
    ("uom.uom", {"updatable": False}),
    ("planning.role", {"updatable": False}),
    ("product.template", {"updatable": False}),
    ("calendar.event", {"is_demo_data": True, "updatable": False}),
    ("crm.tag", {"is_demo_data": True, "updatable": False}),
    ("crm.team", {"is_demo_data": True}),
    ("crm.stage", {"updatable": False}),
    ("crm.lead", {"is_demo_data": True, "updatable": False}),
    ("event.event.ticket", {"updatable": False}),
    ("helpdesk.ticket", {"is_demo_data": True, "updatable": False}),
    ("product.supplierinfo", {"is_demo_data": True, "updatable": False}),
    ("sale.order", {"domain": "[('state', 'not in', ['draft', 'cancel'])]", "is_demo_data": True, "updatable": False}),
    ("sale.order.line", {"is_demo_data": True, "updatable": False}),
    ("loyalty.program", {"is_demo_data": True, "updatable": False}),
    ("loyalty.reward", {"is_demo_data": True, "updatable": False}),
    ("loyalty.rule", {"is_demo_data": True, "updatable": False}),
    ("mail.template", {"updatable": False}),
    ("maintenance.equipment", {"updatable": False}),
    ("mrp.bom", {"is_demo_data": True, "updatable": False}),
    ("mrp.bom.line", {"is_demo_data": True, "updatable": False}),
    ("mrp.production", {"is_demo_data": True, "updatable": False}),
    ("mrp.routing.workcenter", {"is_demo_data": True, "updatable": False}),
    ("mrp.workorder", {"is_demo_data": True, "updatable": False}),
    ("project.task", {"is_demo_data": True, "updatable": False}),
    ("project.project.stage", {}),
    ("product.attribute", {"updatable": False}),
    ("product.packaging", {"updatable": False}),
    ("product.attribute.value", {"updatable": False}),
    ("product.pricelist", {"updatable": False}),
    ("product.pricelist.item", {"updatable": False}),
    ("product.template.attribute.line", {"updatable": False}),
    ("product.template.attribute.value", {"updatable": False}),
    ("product.product", {"updatable": False}),
    ("product.image", {}),
    ("pos.category", {"updatable": False}),
    ("pos.config", {"updatable": False}),
    ("pos.order", {'domain': "[('state', '!=', 'cancel')]", "is_demo_data": True, "updatable": False}),
    ("pos.order.line", {"is_demo_data": True, "updatable": False}),
    ("pos.payment.method", {"updatable": False}),
    ("pos.session", {"is_demo_data": True, "updatable": False}),
    ("pos_preparation_display.display", {"is_demo_data": True, "updatable": False}),
    ("sale.order.template", {"updatable": False}),
    ("sale.order.template.line", {"updatable": False}),
    ("knowledge.cover", {"include_attachment": True, "updatable": False}),
    ("knowledge.article", {"domain": "[('category', 'in', ['workspace', 'shared'])]"}),
    ("website", {"is_demo_data": True, "updatable": False, "domain": "[]"}),
    ("website.page", {"is_demo_data": True, "updatable": False}),
    ("website.menu", {"is_demo_data": True, "updatable": False}),
    ("stock.lot", {"is_demo_data": True}),
    ("purchase.order", {"is_demo_data": True, "updatable": False}),
    ("purchase.order.line", {"is_demo_data": True}),
    ("quality.point", {"updatable": False}),
    ("quality.check", {"is_demo_data": True}),
    ("planning.slot.template", {"is_demo_data": True}),
    ("planning.recurrency", {"is_demo_data": True, "updatable": False}),
    ("planning.slot", {"is_demo_data": True, "updatable": False}),
    ("restaurant.floor", {"updatable": False}),
    ("restaurant.table", {"updatable": False}),
    ("repair.order", {"is_demo_data": True, "updatable": False}),
    ("sign.item", {"updatable": False}),
    ("sign.request", {"updatable": False}),
    ("sign.template", {"updatable": False}),
    ("stock.quant", {"is_demo_data": True, "updatable": False}),
    ("stock.warehouse.orderpoint", {"is_demo_data": True, "updatable": False}),
    ("survey.survey", {"is_demo_data": True, "updatable": False}),
    ("survey.question", {"is_demo_data": True, "updatable": False}),
    ("survey.question.answer", {"is_demo_data": True, "updatable": False}),
]

DEFAULTS_BY_PRESET_MODELS = {
    m[0]: {**m[1], "sequence": index}
    for index, m in enumerate(PRESET_MODELS_DEFAULTS)
}

# _compute_excluded_fields: default fields to exclude
DEFAULT_FIELDS_TO_EXCLUDE = {
    "res.partner": {
        "ocn_token",
        "signup_type",
        "commercial_partner_id",
        "complete_name",
        "calendar_last_notif_ack",
        "category_id",
        "commercial_company_name",
        "customer_rank",
        "email_normalized",
        "phone_sanitized",
        "peppol_eas",
        "peppol_endpoint",
        "contact_address_complete",
        "tz",
    },
    "hr.employee": {"employee_token", "resource_calendar_id", "resource_id"},
    "account.analytic.plan": {"complete_name"},
    "product.category": {"complete_name"},
    "product.product": {
        "combination_indices",
        "image_variant_256",
        "image_variant_512",
        "image_variant_1024",
        "base_unit_count",
    },
    "knowledge.cover": {"attachment_url"},
    "knowledge.article": {
        "root_article_id",
        "last_edition_date",
        "favorite_count",
    },
    "loyalty.rule": {
        "promo_barcode",
        "mode",
    },
    "loyalty.reward": {"description"},
    "stock.quant": {
        "inventory_date",
        "in_date",
    },
    "stock.warehouse.orderpoint": {
        "trigger",
        "name",
        "warehouse_id",
        "location_id",
    },
    "project.project": {"sale_line_id", "rating_request_deadline"},
    "project.task": {"personal_stage_type_ids", "date_last_stage_update"},
    "project.task.type": {"project_ids"},
    "product.attribute.value": {"pav_attribute_line_ids"},
    "product.public.category": {"product_tmpl_ids"},
    "product.template.attribute.value": {
        "ptav_product_variant_ids",
        "product_tmpl_id",
        "attribute_id",
    },
    "product.template.attribute.line": {"value_count"},
    "planning.slot": {
        "access_token",
        "allocated_hours",
        "sale_order_id",
    },
    "sale.order": {
        "name",
        "team_id",
        "transaction_ids",
        "procurement_group_id",
        "require_signature",
        "require_payment",
        "validity_date",
        "note",
        "partner_shipping_id",
        "partner_invoice_id",
        "payment_term_id",
        "state",
        "subscription_state",
        "currency_rate",
        "amount_tax",
        "amount_untaxed",
        "amount_total",
        "amount_to_invoice",
        "invoice_status",
    },
    "sale.order.line": {
        "invoice_lines",
        "product_packaging_id",
        "product_packaging_qty",
        "task_id",
        "price_subtotal",
        "price_tax",
        "price_total",
        "price_reduce_taxexcl",
        "price_reduce_taxinc",
        "qty_delivered_method",
        "qty_delivered",
        "qty_to_invoice",
        "qty_invoiced",
        "invoice_status",
        "untaxed_amount_invoiced",
        "untaxed_amount_to_invoice",
    },
    "purchase.order": {
        "name",
        "origin",
        "invoice_ids",
        "group_id",
        "invoice_count",
        "invoice_status",
        "amount_tax",
        "amount_total",
        "currency_rate",
    },
    "purchase.order.line": {
        "currency_id",
        "product_packaging_id",
        "move_dest_ids",
        "price_subtotal",
        "price_total",
        "price_tax",
        "qty_invoiced",
        "qty_received_method",
        "qty_received",
        "qty_to_invoice",
    },
    "crm.lead": {
        "recurring_plan",
        "title",
        "lost_reason_id",
        "duplicate_lead_ids",
        "lang_id",
        "prorated_revenue",
        "automated_probability",
        "date_last_stage_update",
    },
    "survey.survey": {"session_question_id"},
    "survey.question": {"page_id"},
}

# _compute_excluded_fields: abstract model fields to exclude
ABSTRACT_MODEL_FIELDS_TO_EXCLUDE = {
    "html.field.history.mixin": {"html_field_history_metadata", "html_field_history"},
    "mail.activity.mixin": {"activity_ids"},
    "mail.thread": {"message_follower_ids", "message_ids"},
    "mail.thread.blacklist": {"email_normalized", "is_blacklisted", "message_bounce"},
    "mail.alias.mixin": {"alias_id"},
    "portal.mixin": {"access_url", "access_token", "access_warning"},
    "avatar.mixin": {
        "avatar_1920",
        "avatar_1024",
        "avatar_512",
        "avatar_256",
        "avatar_128",
    },
    # only export image_1920, the other sizes can be generated from it
    "image.mixin": {"image_1024", "image_512", "image_256", "image_128"},
}

# _compute_excluded_fields: relations to exclude
RELATED_MODELS_TO_EXCLUDE = [
    "account.account.tag",
    "account.account",
    "account.bank.statement",
    "account.edi.document",
    "account.fiscal.position",
    "account.full.reconcile",
    "account.journal",
    "account.partial.reconcile",
    "account.payment",
    "account.root",
    "account.tax.repartition.line",
    "account.tax",
]


class StudioExportModel(models.Model):
    _name = "studio.export.model"
    _description = "Studio Export Models"
    _order = "sequence,id"
    _sql_constraints = [
        ("unique_model", "unique(model_id)", "This model is already being exported."),
    ]

    sequence = fields.Integer()
    model_id = fields.Many2one(
        "ir.model",
        required=True,
        ondelete="cascade",
        domain="[('transient', '!=', True), ('abstract', '!=', True)]",
    )
    model_name = fields.Char(string="Model Name", related="model_id.model", store=True)
    excluded_fields = fields.Many2many(
        "ir.model.fields",
        string="Fields to exclude",
        domain="[('model_id', '=', model_id)]",
        compute="_compute_excluded_fields",
        readonly=False,
        store=True,
    )
    domain = fields.Text(default="[]")
    records_count = fields.Char(string="Records", compute="_compute_records_count")
    is_demo_data = fields.Boolean(
        default=False,
        string="Demo",
        help="If set, the exported records will be considered as demo data during the import.",
    )
    updatable = fields.Boolean(
        default=True,
        help="Defines if the records would be updated during a module update.",
    )
    include_attachment = fields.Boolean(
        string="Attachments",
        default=False,
        help="If set, the attachments related to the exported records will be included in the export.",
    )

    @api.depends("model_id")
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.model_id.display_name

    @api.depends("model_id")
    def _compute_excluded_fields(self):
        to_reset = self.filtered(lambda r: not r.model_id)
        to_reset.excluded_fields = None
        for record in self - to_reset:
            RecordModel = self.env[record.model_name]
            fields_not_to_export = DEFAULT_FIELDS_TO_EXCLUDE.get(
                record.model_name, set()
            )

            # also exclude fields of abstract models
            to_search = {m for m in RecordModel._BaseModel__base_classes if m._abstract}
            searched = set()
            while to_search:
                current = to_search.pop()
                if current._name in ABSTRACT_MODEL_FIELDS_TO_EXCLUDE:
                    fields_not_to_export |= ABSTRACT_MODEL_FIELDS_TO_EXCLUDE[current._name]
                searched.add(current)
                to_search |= (
                    {
                        m
                        for m in current._BaseModel__base_classes
                        if m not in searched and m._abstract
                    }
                    if "_BaseModel__base_classes" in dir(current)
                    else set()
                )

            for field_name, field in RecordModel._fields.items():
                if field_name in fields_not_to_export:
                    continue
                # exclude computed fields that can't impact the import
                # exclude one2many fields
                # exclude many2x if comodel is not to export
                # exclude fields created in l10n_* modules
                module = field._modules[0] if field._modules else None
                if (
                    (
                        (field.compute or field.related)
                        and not (field.store or field.company_dependent)
                    )
                    or (field.type == "one2many")
                    or (module and module.startswith("l10n_"))
                    or (
                        field.type in ["many2one", "many2many"]
                        and field.comodel_name in RELATED_MODELS_TO_EXCLUDE
                    )
                ):
                    fields_not_to_export.add(field_name)

            if RecordModel._parent_store:
                fields_not_to_export.add("parent_path")

            fields_not_to_export -= set(FIELDS_TO_EXPORT.get(record.model_name, []))
            excluded_fields = self.env["ir.model.fields"].search(
                [
                    ("model_id", "=", record.model_id.id),
                    ("name", "in", list(fields_not_to_export)),
                ]
            )
            record.excluded_fields = [Command.set(excluded_fields.ids)]

    @api.depends("model_name", "domain")
    def _compute_records_count(self):
        for record in self:
            records_count = (
                self.env[record.model_name].sudo()
                .search_count(literal_eval(record.domain or "[]"))
            )
            record.records_count = _("%s record(s)", records_count)

    def action_preset(self):
        curr_models_names = [
            r["model_name"] for r in self.search_read([], ["model_name"])
        ]
        preset_models = [
            (model, DEFAULTS_BY_PRESET_MODELS.get(model["model"], {}))
            # find all existing models from the preset list + custom ones
            for model in self.env["ir.model"].search_read(
                [
                    ("transient", "=", False),
                    ("abstract", "=", False),
                ]
                + expression.OR(
                    [
                        [("model", "in", list(DEFAULTS_BY_PRESET_MODELS.keys()))],
                        [("model", "=like", r"x\_%")],
                        [("state", "=", "manual")],
                    ]
                ),
                ["model"],
            )
        ]
        to_create = [
            {**defaults, "model_id": model["id"]}
            for model, defaults in preset_models
            # filter out models that are already configured or do not have some records to export
            if model["model"] not in curr_models_names
            and (
                not self.env[model["model"]]._log_access
                or (
                    self.env[model["model"]].sudo()
                    .search_count(literal_eval(defaults.get("domain", "[]")))
                )
            )
        ]

        if to_create:
            self.create(to_create)

    def _get_exportable_records(self):
        self.ensure_one()
        domain = literal_eval(self.domain or "[]")
        model = self.env[self.model_name].sudo()
        return model.search(domain)
