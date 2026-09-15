import ast
import logging

import werkzeug

from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.http import Controller, request, route
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class ModelPageController(Controller):
    pager_step = 20

    @route(
        [
            "/model/<string:page_name_slugified>",
            "/model/<string:page_name_slugified>/page/<int:page_number>",
            "/model/<string:page_name_slugified>/<string:record_slug>",
        ],
        website=True,
        auth="public",
        readonly=True,
    )
    def generic_model(
        self, page_name_slugified=None, page_number=1, record_slug=None, **searches
    ):
        if not page_name_slugified:
            _debug.logic("model_page_refused", reason="no_slug")
            raise werkzeug.exceptions.NotFound

        website = request.website

        website_page_domain = (
            Domain("name_slugified", "=", page_name_slugified)
            & website.website_domain()
        )
        page = request.env["website.controller.page"].search(
            website_page_domain, limit=1
        )
        if not page or (
            not page.website_published
            and not request.env.user.has_group("website.group_website_designer")
        ):
            _debug.logic(
                "model_page_refused",
                reason="unknown_or_unpublished",
                slug=page_name_slugified,
                page=page.id,
            )
            raise werkzeug.exceptions.NotFound

        if record_slug is not None:
            view = page.sudo().record_view_id
        else:
            view = page.sudo().view_id

        if not view:
            _debug.logic(
                "model_page_refused",
                reason="no_view",
                page=page.id,
                record_view=record_slug is not None,
            )
            raise werkzeug.exceptions.NotFound

        target_model_name = page.sudo().model_id.model
        Model = request.env[target_model_name]
        if not Model.has_access("read"):
            _debug.logic(
                "model_page_refused",
                reason="no_read_access",
                page=page.id,
                model=target_model_name,
            )
            raise werkzeug.exceptions.Forbidden

        rec_domain = ast.literal_eval(page.record_domain or "[]")
        domains = [rec_domain]
        implements_published_mixin = "website_published" in Model._fields
        if implements_published_mixin and not request.env.user.has_group(
            "website.group_website_designer"
        ):
            domains.append([("website_published", "=", True)])

        if record_slug:
            return self._render_model_record(
                page, view, Model, domains, record_slug, implements_published_mixin
            )

        layout_mode = request.session.get(f"website_{view.id}_layout_mode")
        if not layout_mode:
            layout_mode = page.default_layout

        searches.setdefault("search", "")
        order = self._get_model_order(Model, searches.get("order"))
        searches["order"] = order

        def record_to_url(record):
            return "/model/%s/%s" % (
                page.name_slugified,
                request.env["ir.http"]._slug(record),
            )

        if searches["search"]:
            name_domain = self._get_model_search_domain(Model, searches["search"])
            if name_domain is not None:
                domains.append(name_domain)

        return self._render_model_listing(
            page,
            view,
            Model,
            Domain.AND(domains),
            searches,
            page_number,
            layout_mode,
            record_to_url,
        )

    def _render_model_listing(
        self,
        page,
        view,
        Model,
        search_domain,
        searches,
        page_number,
        layout_mode,
        record_to_url,
    ):
        order = searches["order"]
        search_count = Model.search_count(search_domain)
        pager = request.website.pager(
            url=f"/model/{page.name_slugified}",
            url_args=searches,
            total=search_count,
            page=page_number,
            step=self.pager_step,
            scope=5,
        )
        if str(page_number).isdecimal() and int(page_number) > pager["page_count"]:
            _debug.logic("model_page_page_clamped", page=page.id, requested=page_number)
            return request.redirect(pager["page_last"]["url"])

        query_order = order
        if not any(term.split()[0] == "id" for term in order.split(",")):
            query_order = f"{order}, id desc"
        with _debug.perf(
            "model_page_records", cr=request.env.cr, model=Model._name
        ) as span:
            records = Model.search(
                search_domain,
                limit=self.pager_step,
                offset=pager["offset"],
                order=query_order,
            )
            span.set(matched=search_count, shown=len(records))

        _debug.pipeline(
            "model_page",
            verdict="listing",
            page=page.id,
            model=Model._name,
            matched=search_count,
            shown=len(records),
            layout=layout_mode,
            search=searches["search"] or None,
        )
        return request.render(
            view.key,
            {
                "order_by": order,
                "search": searches["search"],
                "search_count": search_count,
                "pager": pager,
                "records": records,
                "record_to_url": record_to_url,
                "layout_mode": layout_mode,
                "view_id": view.id,
                "main_object": page.sudo(),
            },
        )

    def _render_model_record(
        self, page, view, Model, domains, record_slug, implements_published_mixin
    ):
        _, res_id = request.env["ir.http"]._unslug(record_slug)
        record = Model.search(Domain("id", "=", res_id) & Domain.AND(domains), limit=1)
        if not record or record_slug != request.env["ir.http"]._slug(record):
            _debug.logic(
                "model_page_refused",
                reason="record_slug_mismatch",
                page=page.id,
                slug=record_slug,
            )
            raise werkzeug.exceptions.NotFound

        _debug.pipeline(
            "model_page",
            verdict="record",
            page=page.id,
            model=Model._name,
            record=record.id,
        )
        return request.render(
            view.key,
            {
                "main_object": page.sudo()
                if not implements_published_mixin
                else record,
                "record": record,
                "listing": {"href": ".", "name": page.name},
            },
        )

    def _get_model_search_domain(self, Model, search):
        search_fnames = set(
            Model._rec_names_search or ([Model._rec_name] if Model._rec_name else [])
        )
        if "seo_name" in Model._fields:
            search_fnames.add("seo_name")
        if not search_fnames:
            _debug.logic("model_page_search_ignored", model=Model._name)
            return None
        return Domain.OR(
            [[(name_field, "ilike", search)] for name_field in search_fnames]
        )

    def _get_model_order(self, model, order):
        default_order = (
            "create_date desc" if "create_date" in model._fields else model._order
        )
        if not order:
            return default_order
        try:
            model._check_qorder(order)
        except UserError:
            _logger.debug("Invalid model page order; using default for %s", model._name)
            _debug.logic(
                "model_page_order_rejected",
                reason="invalid",
                model=model._name,
                order=order,
            )
            return default_order
        for term in order.split(","):
            field = model._fields.get(term.split()[0])
            if not field or not field.store or not field.column_type:
                _debug.logic(
                    "model_page_order_rejected",
                    reason="not_a_stored_column",
                    model=model._name,
                    term=term,
                )
                return default_order
        return order
