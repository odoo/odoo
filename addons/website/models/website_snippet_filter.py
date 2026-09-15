import logging
from ast import literal_eval
from collections import OrderedDict
from random import randint

from lxml import etree, html

from odoo import _, api, fields, models
from odoo.exceptions import MissingError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class WebsiteSnippetFilter(models.Model):
    _name = "website.snippet.filter"
    _inherit = ["mixin.website.published.multi"]
    _description = "Website Snippet Filter"
    _order = "name ASC"

    name = fields.Char(
        translate=True,
        required=True,
    )
    action_server_id = fields.Many2one(
        comodel_name="ir.actions.server",
        string="Server Action",
        ondelete="cascade",
    )
    field_names = fields.Char(
        default="",
        required=True,
        help="A list of comma-separated field names",
    )
    filter_id = fields.Many2one(
        comodel_name="ir.filters",
        ondelete="cascade",
    )
    limit = fields.Integer(
        required=True,
        help="The limit is the maximum number of records retrieved",
    )
    website_id = fields.Many2one(
        comodel_name="website",
        ondelete="cascade",
    )
    model_name = fields.Char(
        string="Model name",
        compute="_compute_model_name",
    )
    help = fields.Text(
        string="Description",
        translate=True,
        help="Optional help text describing the filter usage and/or purpose.",
    )

    @api.depends("filter_id", "action_server_id")
    def _compute_model_name(self):
        for snippet_filter in self:
            if snippet_filter.filter_id:
                snippet_filter.model_name = snippet_filter.filter_id.model_id
            else:
                snippet_filter.model_name = (
                    snippet_filter.action_server_id.model_id.model
                )

    @api.constrains("action_server_id", "filter_id")
    def _check_data_source_is_provided(self):
        for record in self:
            if bool(record.action_server_id) == bool(record.filter_id):
                _debug.logic(
                    "snippet_filter_refused",
                    reason="ambiguous_data_source",
                    filter=record.id,
                )
                raise ValidationError(
                    _("Either action_server_id or filter_id must be provided.")
                )

    @api.constrains("limit")
    def _check_limit(self):
        for record in self:
            if not 0 < record.limit <= 16:
                _debug.logic(
                    "snippet_filter_refused",
                    reason="limit_out_of_range",
                    filter=record.id,
                    limit=record.limit,
                )
                raise ValidationError(_("The limit must be between 1 and 16."))

    @api.constrains("field_names")
    def _check_field_names(self):
        for record in self:
            for field_name in record.field_names.split(","):
                if not field_name.strip():
                    raise ValidationError(
                        _("Empty field name in “%s”", record.field_names)
                    )

    def _render(
        self,
        template_key=None,
        limit=None,
        search_domain=None,
        with_sample=False,
        res_model=None,
        res_id=None,
        **custom_template_data,
    ):
        self and self.check_singleton()

        if not template_key or ".dynamic_filter_template_" not in template_key:
            _debug.logic(
                "snippet_render_refused",
                reason="not_a_dynamic_filter_template",
                template=template_key,
            )
            return []
        if (
            not self.env["ir.ui.view"]
            .sudo()
            ._get_template_view(template_key, raise_if_not_found=False)
        ):
            _debug.logic(
                "snippet_render_refused",
                reason="unknown_template",
                template=template_key,
            )
            return []
        if search_domain is None:
            search_domain = []

        if (
            self.website_id
            and self.env["website"].get_current_website() != self.website_id
        ):
            _debug.logic(
                "snippet_render_refused",
                reason="other_website",
                filter=self.id,
                website=self.website_id.id,
            )
            return []

        if self.model_name and self.model_name.replace(".", "_") not in template_key:
            _debug.logic(
                "snippet_render_refused",
                reason="template_model_mismatch",
                model=self.model_name,
                template=template_key,
            )
            return []

        records = self._prepare_values(
            limit=limit, search_domain=search_domain, res_model=res_model, res_id=res_id
        )
        is_sample = with_sample and not records
        if is_sample:
            records = self._prepare_sample(limit, res_model=res_model)
        _debug.pipeline(
            "snippet_filter_rendered",
            filter=self.id,
            template=template_key,
            records=len(records or ()),
            sample=is_sample,
        )
        content = (
            self.env["ir.qweb"]
            .with_context(inherit_branding=False)
            ._render(
                template_key,
                dict(
                    records=records,
                    is_sample=is_sample,
                    **custom_template_data,
                ),
            )
        )
        return [
            etree.tostring(el, encoding="unicode", method="html")
            for el in list(html.fromstring("<root>%s</root>" % str(content)))
        ]

    @staticmethod
    def _coerce_positive_int(value):
        if isinstance(value, bool) or not isinstance(value, (int, str, float)):
            return None
        try:
            value = int(value)
        except TypeError, ValueError:
            return None
        return value if value > 0 else None

    def _prepare_values(self, limit=None, search_domain=None, **options):
        self and self.check_singleton()

        model_name = self.filter_id.sudo().model_id or options.get("res_model")
        res_id = self._coerce_positive_int(options.get("res_id"))
        max_limit = max(self.limit, 16)
        limit = self._coerce_positive_int(limit)
        limit = (limit and min(limit, max_limit)) or max_limit
        single_record_filter = limit == 1 and model_name and res_id

        if self.filter_id or single_record_filter:
            model = self._resolve_model(model_name)
            if model is None:
                _debug.logic(
                    "snippet_values_refused",
                    reason="unknown_model",
                    filter=self.id,
                    model=model_name,
                )
                return []
            filter_sudo = self.filter_id.sudo()
            if single_record_filter:
                domain = Domain("id", "=", res_id)
                context = {}
                order = None
            else:
                domain = Domain(filter_sudo._get_domain_evaluated())
                context = self.env["ir.actions.actions"]._eval_action_context(
                    filter_sudo.context
                )
                order = ",".join(literal_eval(filter_sudo.sort)) or None
            if "website_id" in model:
                domain &= self.env["website"].get_current_website().website_domain()
            if "company_id" in model:
                website = self.env["website"].get_current_website()
                domain &= Domain("company_id", "in", [False, website.company_id.id])
            if "is_published" in model:
                domain &= Domain("is_published", "=", True)
            if search_domain:
                search_domain = Domain(search_domain)
                for condition in search_domain.iter_conditions():
                    field_expr = condition.field_expr
                    if "." in field_expr or field_expr not in model._fields:
                        _debug.logic(
                            "snippet_search_domain_refused",
                            filter=self.id,
                            field=field_expr,
                        )
                        raise ValueError(
                            f"Invalid field {field_expr!r} in search domain"
                        )
                domain &= search_domain
            try:
                with _debug.perf(
                    "snippet_filter_records",
                    cr=self.env.cr,
                    filter=self.id,
                    model=model._name,
                    limit=limit,
                ) as span:
                    records = (
                        model.sudo(False)
                        .with_context(**context)
                        .search(domain, order=order, limit=limit)
                    )
                    span.set(records=len(records))
                return self._filter_records_to_values(
                    records.sudo(), res_model=model_name
                )
            except MissingError:
                if not single_record_filter:
                    _logger.warning(
                        "The provided domain %s in 'ir.filters' generated a MissingError in '%s'",
                        domain,
                        self._name,
                    )
                _debug.logic(
                    "snippet_filter_missing_records",
                    filter=self.id,
                    single=single_record_filter,
                )
                return []
        elif self.action_server_id:
            return self._prepare_values_from_action(limit, search_domain)
        return None

    def _prepare_values_from_action(self, limit, search_domain):
        try:
            with _debug.perf(
                "snippet_filter_action",
                cr=self.env.cr,
                filter=self.id,
                action=self.action_server_id.id,
            ):
                return (
                    self.action_server_id.with_context(
                        dynamic_filter=self,
                        limit=limit,
                        search_domain=search_domain,
                    )
                    .sudo()
                    .run()
                    or []
                )
        except MissingError:
            _logger.warning(
                "The provided domain %s in 'ir.actions.server' generated a MissingError in '%s'",
                search_domain,
                self._name,
            )
            _debug.logic(
                "snippet_action_missing_records",
                filter=self.id,
                action=self.action_server_id.id,
            )
            return []

    def _get_field_name_and_type(self, model, field_name):
        field_name, _sep, field_widget = field_name.partition(":")
        if field_widget:
            return field_name, field_widget
        field = model._fields.get(field_name)
        if field:
            field_type = field.type
        elif "image" in field_name:
            field_type = "image"
        elif "price" in field_name:
            field_type = "monetary"
        else:
            field_type = "text"
        return field_name, field_type

    def _get_filter_meta_data(self, model):
        meta_data = OrderedDict({})
        field_names = self.field_names or self.with_context(
            model=model._name
        ).default_get(["field_names"]).get("field_names")
        for field_name in (field_names or "").split(","):
            field_name = field_name.strip()
            if not field_name:
                continue
            field_name, field_widget = self._get_field_name_and_type(model, field_name)
            meta_data[field_name] = field_widget
        return meta_data

    def _prepare_sample(self, length=6, **options):
        if not length:
            return []
        records = self._prepare_sample_records(length, **options)
        options["is_sample"] = True
        return self._filter_records_to_values(records, **options)

    def _resolve_model(self, model_name):
        if not isinstance(model_name, str) or model_name not in self.env:
            return None
        return self.env[model_name]

    def _prepare_sample_records(self, length, **options):
        if not length:
            return []

        sample = []
        model = self._resolve_model(self.model_name or options.get("res_model"))
        if model is None:
            return []
        sample_data = self._get_hardcoded_sample(model)
        if sample_data:
            for index in range(length):
                single_sample_data = sample_data[index % len(sample_data)].copy()
                self._update_sample(model, single_sample_data, index)
                sample.append(model.new(single_sample_data))
        return sample

    def _update_sample(self, model, sample, index):
        meta_data = self._get_filter_meta_data(model)
        for field_name, field_widget in meta_data.items():
            if field_name not in sample and field_name in model:
                if field_widget in ("image", "binary"):
                    sample[field_name] = None
                elif field_widget == "monetary":
                    sample[field_name] = randint(100, 10000) / 10.0
                elif field_widget in ("integer", "float"):
                    sample[field_name] = index
                else:
                    sample[field_name] = _("Sample %s", index + 1)
        return sample

    def _get_hardcoded_sample(self, model):
        return [{}]

    def _filter_records_to_values(self, records, **options):
        self and self.check_singleton()
        model = self._resolve_model(self.model_name or options.get("res_model"))
        if model is None:
            return []
        meta_data = self._get_filter_meta_data(model)

        values = []
        Website = self.env["website"]
        for record in records:
            data = {}
            for field_name, field_widget in meta_data.items():
                field = model._fields.get(field_name)
                if field and field.type in ("binary", "image"):
                    if options.get("is_sample"):
                        data[field_name] = (
                            record[field_name].decode("utf8")
                            if field_name in record
                            else "/web/image"
                        )
                    else:
                        data[field_name] = Website.image_url(record, field_name)
                elif field_widget == "monetary":
                    model_currency = None
                    if field and field.type == "monetary":
                        model_currency = record[field.get_currency_field(record)]
                    elif "currency_id" in model._fields:
                        model_currency = record["currency_id"]
                    if model_currency:
                        website_currency = self._get_website_currency()
                        data[field_name] = model_currency._convert(
                            record[field_name],
                            website_currency,
                            Website.get_current_website().company_id,
                            fields.Date.today(),
                        )
                    else:
                        data[field_name] = record[field_name]
                else:
                    data[field_name] = record[field_name]

            data["call_to_action_url"] = (
                "website_url" in record and record["website_url"]
            )
            data["_record"] = record
            values.append(data)
        return values

    @api.model
    def _get_website_currency(self):
        company = self.env["website"].get_current_website().company_id
        return company.currency_id
