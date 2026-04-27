# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter, OrderedDict, defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import topological_sort
from odoo.tools.misc import OrderedSet


# List of models to export (the order ensures that dependencies are satisfied)
DEFAULT_MODELS_TO_EXPORT = [
    "res.groups",
    "report.paperformat",
    "ir.model",
    "ir.model.fields",
    "ir.ui.view",
    "ir.actions.act_window",
    "ir.actions.act_window.view",
    "ir.actions.report",
    "mail.template",
    "ir.actions.server",
    "ir.ui.menu",
    "ir.filters",
    "base.automation",
    "ir.model.access",
    "ir.rule",
    "ir.default",
    "studio.approval.rule",
]

# List of fields to export by model
FIELDS_TO_EXPORT = {
    "base.automation": [
        "action_server_ids",
        "active",
        "description",
        "filter_domain",
        "filter_pre_domain",
        "last_run",
        "log_webhook_calls",
        "model_id",
        "name",
        "on_change_field_ids",
        "record_getter",
        "trg_date_id",
        "trg_date_range_type",
        "trg_date_range",
        "trg_field_ref",
        "trg_selection_field_id",
        "trigger_field_ids",
        "trigger",
    ],
    "ir.actions.act_window": [
        "binding_model_id",
        "binding_type",
        "binding_view_types",
        "context",
        "domain",
        "filter",
        "groups_id",
        "help",
        "limit",
        "name",
        "res_model",
        "search_view_id",
        "target",
        "type",
        "usage",
        "view_id",
        "view_mode",
    ],
    "ir.actions.act_window.view": [
        "act_window_id",
        "multi",
        "sequence",
        "view_id",
        "view_mode",
    ],
    "ir.actions.report": [
        "attachment",
        "attachment_use",
        "binding_model_id",
        "binding_type",
        "binding_view_types",
        "groups_id",
        "model",
        "multi",
        "name",
        "paperformat_id",
        "report_name",
        "report_type",
    ],
    "ir.actions.server": [
        "binding_model_id",
        "binding_type",
        "binding_view_types",
        "child_ids",
        "code",
        "crud_model_id",
        "evaluation_type",
        "groups_id",
        "help",
        "link_field_id",
        "model_id",
        "name",
        "resource_ref",
        "selection_value",
        "sequence",
        "state",
        "update_boolean_value",
        "update_field_id",
        "update_m2m_operation",
        "update_path",
        "usage",
        "value",
        "webhook_field_ids",
        "webhook_url",
    ],
    "ir.filters": [
        "action_id",
        "active",
        "context",
        "domain",
        "is_default",
        "model_id",
        "name",
        "sort",
    ],
    "ir.model": [
        "info",
        "is_mail_thread",
        "is_mail_activity",
        "model",
        "name",
        "state",
        "transient",
    ],
    "ir.model.access": [
        "active",
        "group_id",
        "model_id",
        "name",
        "perm_create",
        "perm_read",
        "perm_unlink",
        "perm_write",
    ],
    "ir.model.fields": [
        "complete_name",
        "compute",
        "copied",
        "depends",
        "domain",
        "field_description",
        "groups",
        "group_expand",
        "help",
        "index",
        "model",
        "model_id",
        "name",
        "on_delete",
        "readonly",
        "related",
        "relation",
        "relation_field",
        "relation_table",
        "required",
        "selectable",
        "selection",
        "size",
        "state",
        "store",
        "tracking",
        "translate",
        "ttype",
        "currency_field",
    ],
    "ir.rule": [
        "active",
        "domain_force",
        "groups",
        "model_id",
        "name",
        "perm_create",
        "perm_read",
        "perm_unlink",
        "perm_write",
    ],
    "ir.ui.menu": [
        "action",
        "active",
        "groups_id",
        "name",
        "parent_id",
        "sequence",
        "web_icon",
        "web_icon_data",
    ],
    "ir.ui.view": [
        "active",
        "arch",
        "groups_id",
        "inherit_id",
        "key",
        "mode",
        "model",
        "name",
        "priority",
        "type",
        "website_id",
    ],
    "mail.template": [
        "auto_delete",
        "body_html",
        "email_cc",
        "email_from",
        "email_to",
        "lang",
        "model_id",
        "name",
        "partner_to",
        "ref_ir_act_window",
        "reply_to",
        "report_template_ids",
        "scheduled_date",
        "subject",
        "use_default_to",
    ],
    "res.groups": ["color", "comment", "implied_ids", "name", "share"],
    "ir.default": ["field_id", "condition", "json_value"],
    "studio.approval.rule": [
        "approver_ids",
        "approval_group_id",
        "model_id",
        "method",
        "action_id",
        "name",
        "message",
        "exclusive_user",
        "domain",
        "can_validate",
    ],
    # Only use for export attachment config in studio export models
    "ir.attachment": [
        "name",
        "type",
        "datas",
        "url",
        "res_id",
        "res_model",
        "res_field",
        "access_token",
        "key",
        "website_id",
    ],
    "mail.message": [
        "subject",
        "res_id",
        "model",
        "body",
        "message_type",
        "subtype_id",
        "author_id",
        "attachment_ids",
    ],
}

# List of models to mark as noupdate.
MODELS_WITH_NOUPDATE = [
    "ir.attachment",
    "ir.rule",
]

# List of relational fields NOT to export, by model.
RELATIONS_NOT_TO_EXPORT = {
    "base.automation": ["trg_date_calendar_id"],
    "ir.actions.server": ["partner_ids"],
    "ir.filters": ["user_id"],
    "mail.template": ["attachment_ids", "mail_server_id"],
    "report.paperformat": ["report_ids"],
    "res.groups": ["category_id", "users"],
}


def _find_circular_dependencies(elems):
    """Return a list of circular dependencies encountered in `elems`.

    :param elems: specifies the elements to sort with their dependencies; it is
        a dictionary like `{element: dependencies}`.

    :returns: a list of lists of elements forming circular dependencies.
    """
    circular_dependencies = []

    def traverse(elem, visited, stack):
        visited.add(elem)
        stack.append(elem)

        if elem in elems:
            for dependency in elems[elem]:
                if dependency == elem:
                    continue
                if dependency not in visited and not traverse(dependency, visited, stack):
                    return False
                if dependency == stack[0]:
                    stack.append(dependency)
                    circular_dependencies.append(stack.copy())
                    return False

        stack.remove(elem)
        return True

    to_skip = set()
    for element in elems:
        if element not in to_skip and not traverse(element, set(), []):
            to_skip.update(circular_dependencies[-1])

    return circular_dependencies


def _get_attachment_fields(env, model):
    def is_attachment_field(info):
        return "relation" in info and info["relation"] == "ir.attachment"

    Model = env[model]
    return [f for f in Model.fields_get().items() if is_attachment_field(f[1])]


class StudioExportWizardData(models.TransientModel):
    """The wizard data resembles the ir.model.data model.
    It is used to store the export data for the wizard,
    even for data that do not have an xmlid (an ir.model.data record).
    """
    _name = "studio.export.wizard.data"
    _description = "Studio Export Data"
    _order = "model_name, res_id"

    model = fields.Char(required=True)
    model_name = fields.Char(
        string="Model Description", compute="_compute_model_name", store=True
    )
    res_id = fields.Many2oneReference(model_field="model", required=True)
    name = fields.Char("Record Name", readonly=True)
    xmlid = fields.Char("External ID", readonly=True)
    pre = fields.Boolean(default=False, readonly=True)
    post = fields.Boolean(default=False, readonly=True)
    studio = fields.Boolean(default=False, readonly=True)
    is_demo_data = fields.Boolean(
        default=False,
        string="As Demo",
        readonly=True,
    )

    @api.depends("model")
    def _compute_model_name(self):
        models = self.mapped("model")
        ir_models = self.env["ir.model"].search([("model", "in", models)])
        for rec in self:
            rec.model_name = ir_models.filtered(lambda r: r.model == rec.model).name

    @api.model_create_multi
    def create(self, vals_list):
        """Compute the needed names and xmlids for the records."""
        models = defaultdict(list)
        for vals in vals_list:
            models[vals["model"]].append(vals["res_id"])

        if "ir.actions.actions" in models:
            # We should replace "ir.actions.actions" records by their proper
            # models, as we never want to export an abstract ir.actions.actions
            # but instead the concrete actions models.
            actions_by_type = self.env["ir.actions.actions"].sudo().browse(models["ir.actions.actions"])._get_actions_by_type()
            types_by_action_id = defaultdict(str)
            for action_type, actions in actions_by_type.items():
                models[action_type].extend(actions.ids)
                types_by_action_id.update(dict.fromkeys(actions.ids, action_type))
            models.pop("ir.actions.actions")

        names = defaultdict(dict)
        xmlids = defaultdict(dict)
        deleted = defaultdict(list)
        for model, res_ids in models.items():
            records = self.env[model].sudo().browse(res_ids)
            existing = records.exists()
            deleted[model] = [r.id for r in records - existing]
            names[model] = {r.id: r.display_name for r in existing}
            xmlids[model] = records._get_external_ids()

        vals_list = [vals for vals in vals_list if not vals["res_id"] in deleted[vals["model"]]]
        for vals in vals_list:
            if vals["model"] == "ir.actions.actions":
                vals["model"] = types_by_action_id[vals["res_id"]]
            model = vals["model"]
            res_id = vals["res_id"]
            vals["name"] = names[model][res_id]
            vals["xmlid"] = (
                xmlids[model][res_id]
                or ["__export__.%s_%s" % (model.replace(".", "_"), res_id)]
            )[0]

        return super().create(vals_list)

    def _xmlid_for_export(self):
        self.ensure_one()
        return self.xmlid.replace('__export__.', '').replace('studio_customization.', '')


class StudioExportWizard(models.TransientModel):
    _name = "studio.export.wizard"
    _description = "Studio Export Wizard"

    def _default_studio_export_data(self):
        data = self.env["ir.model.data"].search([
            ("studio", "=", True),
            ("model", "in", DEFAULT_MODELS_TO_EXPORT),
        ])
        return self.env["studio.export.wizard.data"].create(
            [{"model": d.model, "res_id": d.res_id, "studio": d.studio} for d in data]
        )

    default_export_data = fields.Many2many(
        "studio.export.wizard.data",
        default=_default_studio_export_data,
        relation="rel_studio_export_wizard_data",
    )

    include_additional_data = fields.Boolean(default=False, string="Include Data")
    include_demo_data = fields.Boolean(default=False, string="Include Demo Data")

    additional_models = fields.Many2many(
        "studio.export.model",
        compute="_compute_additional_models",
        string="Additional models to export",
        help="Additional models you may choose to export in addition to the Studio customizations",
    )
    additional_export_data = fields.Many2many(
        "studio.export.wizard.data",
        compute="_compute_export_data",
        relation="rel_studio_export_wizard_additional_data",
    )

    @api.constrains("default_export_data")
    def _check_export_data(self):
        for rec in self:
            data = rec.default_export_data | rec.additional_export_data
            for model, records in data.grouped("model").items():
                if len(records) != len(set(records.mapped("res_id"))):
                    raise ValidationError(_("Model '%s' should not contain records with the same ID.", model))

    @api.depends("include_additional_data", "include_demo_data")
    def _compute_additional_models(self):
        to_update = self.filtered("include_additional_data")
        (self - to_update).additional_models = False
        for record in to_update:
            domain = [("is_demo_data", "=", False)] if not record.include_demo_data else []
            record.additional_models = self.env["studio.export.model"].search(domain)

    @api.depends("additional_models", "default_export_data")
    def _compute_export_data(self):
        """
        Compute the list of records that are exported in addition to the ones
        defined in the default export data. (a.k.a. "not from the studio customizations ones")
        """
        to_update = self.filtered("additional_models")
        (self - to_update).additional_export_data = False
        for rec in to_update:
            export_data_vals = []

            def add(export_model, model, records, pre=False, post=False):
                nonlocal export_data_vals
                model_default_data_ids = rec.default_export_data.filtered(
                    lambda r: r.model == model
                ).mapped("res_id")

                # FIXME: This prevents the same record to be exported multiple times
                # but what do we do if the first record is demo and the second not?
                model_default_data_ids += [
                    export_data["res_id"]
                    for export_data in export_data_vals
                    if export_data["model"] == model
                ]

                export_data_vals += [
                    {
                        "model": model,
                        "res_id": res_id,
                        "is_demo_data": export_model.is_demo_data,
                        "pre": pre,
                        "post": post,
                    }
                    for res_id in records.ids
                    if res_id not in model_default_data_ids
                ]

            for export_model in rec.additional_models.sorted("sequence"):
                to_export = export_model._get_exportable_records()
                if to_export is None:
                    continue
                add(export_model, export_model.model_name, to_export)

                if export_model.model_name == "website":
                    attachments = self.env["ir.attachment"].search(
                        [
                            ("type", "=", "binary"),
                            ("website_id", "in", to_export.ids),
                            "!",
                            ("name", "=like", "%.js.map"),
                            "!",
                            ("name", "=like", "%.css.map"),
                            (
                                "mimetype",
                                "not in",
                                ["application/javascript", "text/css", "text/plain"],
                            ),
                        ]
                    )
                    add(export_model, "ir.attachment", attachments, post=True)

                    website_views = self.env["ir.ui.view"].search(
                        [
                            ("website_id", "in", to_export.ids),
                            ("arch_updated", "=", True),
                        ]
                    )
                    add(export_model, "ir.ui.view", website_views)

                if export_model.model_name == "worksheet.template":
                    model_data = to_export.model_id
                    add(export_model, "ir.model", model_data)

                    model_rule_data = to_export.model_id.mapped("rule_ids")
                    add(export_model, "ir.rule", model_rule_data)

                    model_access_data = to_export.model_id.mapped("access_ids")
                    add(export_model, "ir.model.access", model_access_data)

                    model_group_data = to_export.model_id.mapped("rule_ids").mapped(
                        "groups"
                    )
                    add(export_model, "res.groups", model_group_data)

                    view_data = self.env["ir.ui.view"].search(
                        [("model", "in", to_export.model_id.mapped("model"))]
                    )
                    add(export_model, "ir.ui.view", view_data)

                    action_data = to_export.action_id
                    add(export_model, "ir.actions.act_window", action_data)

                    field_data = to_export.model_id.field_id.filtered_domain(
                        [("state", "!=", "base")]
                    )
                    add(export_model, "ir.model.fields", field_data)

                if export_model.model_name == "project.task.type":
                    mail_templates = to_export.mail_template_id
                    add(export_model, "mail.template", mail_templates)

                # add attachments
                if export_model.include_attachment:
                    fields = _get_attachment_fields(self.env, export_model.model_name)
                    pre_attachments = self.env["ir.attachment"].search(
                        [
                            ("res_id", "in", to_export.ids),
                            ("res_model", "=", export_model.model_name),
                            "|",
                            (
                                "res_field",
                                "in",
                                [f[0] for f in fields if f[1]["type"] != "one2many"],
                            ),
                            ("res_field", "=", False),
                        ]
                    )
                    add(export_model, "ir.attachment", pre_attachments, pre=True)
                    other_attachments = self.env["ir.attachment"].search(
                        [
                            ("res_id", "in", to_export.ids),
                            ("res_model", "=", export_model.model_name),
                            (
                                "res_field",
                                "in",
                                [f[0] for f in fields if f[1]["type"] == "one2many"],
                            ),
                        ]
                    )
                    add(export_model, "ir.attachment", other_attachments, post=True)

            rec.additional_export_data = self.env["studio.export.wizard.data"].create(
                export_data_vals
            )

    def _get_export_info(self):
        """
        Gather all the data to export from the wizard and return it in the correct order.

        :return: A tuple containing the data to export, the list of xml files to generate and
                 the list of circular dependencies found.
        :rtype: tuple
        """
        self.ensure_one()
        all_data = self.default_export_data | self.additional_export_data
        no_update_models = MODELS_WITH_NOUPDATE + self.additional_models.filtered(lambda r: not r.updatable).mapped("model_name")
        pre_export = []
        export = []
        post_export = []

        path_counter = Counter()
        models_to_export, circular_dependencies = self._get_models_to_export()
        for model, is_demo, fields_by_group, data, real_records in models_to_export:

            def add(info, records_data, suffix="", force_exclude=[]):
                if not records_data:
                    return

                res_ids = records_data.mapped("res_id")
                records = real_records.filtered(lambda r: r.id in res_ids)

                for group in ["data", "demo"]:
                    if group not in fields_by_group:
                        continue

                    group_fields = fields_by_group[group]
                    for field_to_exclude in force_exclude:
                        if field_to_exclude in group_fields:
                            group_fields.remove(field_to_exclude)

                    path_info = (group, model.replace(".", "_"), suffix)
                    path_count = path_counter[path_info]
                    path_counter[path_info] += 1
                    path = "%s/%s%s%s.xml" % (
                        group,
                        model.replace(".", "_"),
                        "" if not path_count else f"_{path_count}",
                        suffix,
                    )
                    no_update = model in no_update_models
                    info.append((model, path, records, group_fields, no_update))

            pre_records = data.filtered("pre")
            post_records = data.filtered("post")
            data_records = data - pre_records - post_records

            force_exclude = (
                ["res_id", "res_model", "res_field", "website_id"]
                if model == "ir.attachment"
                else []
            )
            add(pre_export, pre_records, suffix="_pre", force_exclude=force_exclude)
            add(export, data_records)
            add(post_export, post_records, suffix="_post")

        return all_data, pre_export + export + post_export, circular_dependencies

    def _get_fields_to_export_by_models(self):
        """Return a dict of {model_name: [fields_to_export]}"""
        self.ensure_one()
        all_data = self.default_export_data | self.additional_export_data
        model_names = set(all_data.mapped("model"))
        result = {}
        for model_name in model_names:
            Model = self.env[model_name]
            fields_to_export = [
                field
                for field in FIELDS_TO_EXPORT.get(model_name, [])
                if field in Model._fields
            ]

            if not fields_to_export:
                # deduce the fields_to_export from available data
                fields_to_export = list(
                    OrderedSet(Model._fields.keys()) - OrderedSet(models.MAGIC_COLUMNS)
                )

            if RELATIONS_NOT_TO_EXPORT.get(model_name):
                fields_to_export = list(
                    OrderedSet(fields_to_export)
                    - OrderedSet(RELATIONS_NOT_TO_EXPORT.get(model_name))
                )

            # Remove the excluded fields from fields_to_export
            export_model = self.additional_models.filtered(
                lambda m: m.model_name == model_name
            )
            export_model_fields_to_exclude = export_model.excluded_fields.mapped("name")
            fields_to_export = [
                f for f in fields_to_export if f not in export_model_fields_to_exclude
            ]

            # Sort
            fields_details = Model.fields_get(fields_to_export)
            field_deps = OrderedDict.fromkeys(fields_to_export)
            for field in fields_to_export:
                field_deps[field] = (
                    [f.split(".")[0] for f in fields_details[field]["depends"]]
                    if field in fields_details
                    else list()
                )

            result[model_name] = topological_sort(field_deps)

        return result

    def _get_models_to_export(self):
        """
        Returns a sorted list of tuple (model_name, is_demo, groups_to_export)
        The groups_to_export is a list of tuple ("data"|"demo", fields_to_export)
        """
        self.ensure_one()
        fields_by_models = self._get_fields_to_export_by_models()
        result = []
        circular_dependencies = []
        all_data = self.default_export_data | self.additional_export_data

        # (*) Important that we do demo data before master data
        for is_demo in [True, False]:
            data = all_data.filtered(lambda r: r.is_demo_data == is_demo)
            current_models = set(data.mapped("model"))
            model_names = [m for m in DEFAULT_MODELS_TO_EXPORT if m in current_models]
            model_names += sorted([m for m in current_models if m not in model_names])

            # Note that here we can use the result in construction
            # as we have already done the demo data, see (*) above.
            demo_records = {m: records for (m, demo, _, _, records) in result if demo}

            model_grouped_fields = {}
            model_data = {}
            model_records = {}
            for model in model_names:
                model_grouped_fields[model] = self._get_groups_fields(model, is_demo, fields_by_models[model], demo_records)
                model_data[model] = data.filtered(lambda r: r.model == model)
                sudo_model = self.env[model].sudo()
                model_records[model] = sudo_model.browse(model_data[model].mapped("res_id"))

            models_deps = OrderedDict().fromkeys(model_names)
            for model in model_names:
                models_deps[model] = set()
                for field_name, info in sorted(self.env[model].fields_get().items(), key=lambda item: item[0]):
                    if (
                        field_name not in model_grouped_fields[model]["demo" if is_demo else "data"]
                        or "relation" not in info
                        or info["type"] == "one2many"
                    ):
                        continue

                    related_model = info.get("relation")
                    if model_records[model].filtered(lambda r: (
                        related_model in model_records
                        and set(r[field_name].ids).intersection(set(model_records[related_model].ids))
                    )):
                        models_deps[model].add(related_model)

            for circular_dependency in _find_circular_dependencies(models_deps):
                circular_dependencies.append((is_demo, circular_dependency))
            for model in topological_sort(models_deps):
                result.append((model, is_demo, model_grouped_fields[model], model_data[model], model_records[model]))

        return result, circular_dependencies

    def _get_groups_fields(self, model, is_demo, fields_to_export, demo_records):
        self.ensure_one()

        if is_demo:
            return {"demo": fields_to_export}

        all_data = self.default_export_data | self.additional_export_data

        # For master data (non demo) we do not want to export fields
        # related to demo records, if any.
        # Instead we want to export the master data records ALSO as demo
        # but only with the fields related to demo records.
        fields_relations = {
            field_name: field_info["relation"]
            for (field_name, field_info) in self.env[model]
            .fields_get(fields_to_export)
            .items()
            if field_info.get("relation") and field_info["relation"] != model
        }
        demo_fields_to_export = []
        new_fields_to_export = []
        for field_name in fields_to_export:
            related_model = fields_relations.get(field_name)
            if related_model in demo_records:
                data = all_data.filtered(lambda r: r.model == model and not r.is_demo_data)
                records = self.env[model].sudo().browse(data.mapped("res_id"))
                if any(r[field_name] in demo_records[related_model] for r in records):
                    demo_fields_to_export.append(field_name)
                    continue
            new_fields_to_export.append(field_name)

        return {"data": new_fields_to_export, "demo": demo_fields_to_export}

    @api.onchange("include_additional_data")
    def _onchange_include_additional_data(self):
        if not self.include_additional_data:
            self.include_demo_data = False

    @api.onchange("include_demo_data")
    def _onchange_include_demo_data(self):
        if self.include_demo_data:
            self.include_additional_data = True
