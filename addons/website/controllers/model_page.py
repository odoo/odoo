import ast

import werkzeug

from odoo.http import Controller, request, route
from odoo.osv.expression import AND, OR
from odoo.addons.mail.tools.parser import domain_eval


class ModelPageController(Controller):
    pager_step = 20

    @route([
        "/model/<string:page_name_slugified>",
        "/model/<string:page_name_slugified>/page/<int:page_number>",
        "/model/<string:page_name_slugified>/<string:record_slug>",
    ], website=True, auth="public", readonly=True)
    def generic_model(self, page_name_slugified=None, page_number=1, record_slug=None, **searches):
        if not page_name_slugified:
            raise werkzeug.exceptions.NotFound()

        website = request.website

        website_page_domain = AND([
            [("name_slugified", "=", page_name_slugified)],
            website.website_domain(),
        ])

        page = request.env["website.controller.page"].search(website_page_domain, limit=1)
        if not page or\
            (not page.website_published and not request.env.user.has_group('website.group_website_designer')):
            raise werkzeug.exceptions.NotFound()

        if record_slug is not None:
            view = page.sudo().record_view_id
        else:
            view = page.sudo().view_id

        if not view:
            raise werkzeug.exceptions.NotFound()

        target_model_name = page.sudo().model_id.model
        Model = request.env[target_model_name]
        if not Model.has_access("read"):
            raise werkzeug.exceptions.Forbidden()

        rec_domain = domain_eval(page.record_domain or "[]")
        domains = [rec_domain]
        implements_published_mixin = "website_published" in Model._fields
        if implements_published_mixin and not request.env.user.has_group('website.group_website_designer'):
            domains.append([("website_published", "=", True)])

        if record_slug:
            _, res_id = request.env['ir.http']._unslug(record_slug)
            record = Model.browse(res_id).filtered_domain(AND(domains))
            # We check for slug matching because we are not entirely sure
            # that we end up seeing record for the right model
            # i.e. in case of a redirect when a "single" page doesn't match the listing
            if not record.exists() or record_slug != request.env['ir.http']._slug(record):
                raise werkzeug.exceptions.NotFound()

            render_context = {
                "main_object": page.sudo() if not implements_published_mixin else record,  # The template reads some fields that are actually on view
                "record": record,
                "listing": {
                    'href': '.',
                    'name': page.name
                }
            }
            return request.render(view.key, render_context)

        layout_mode = request.session.get(f'website_{view.id}_layout_mode')
        if not layout_mode:
            # use the default layout set for this page
            layout_mode = page.default_layout

        searches.setdefault("search", "")
        searches.setdefault("order", "create_date desc")

        def record_to_url(record):
            return "/model/%s/%s" % (page.name_slugified, request.env['ir.http']._slug(record))

        if searches["search"]:
            # _name_search doesn't take offset, we reimplement the logic that builds the name domain here
            search_fnames = set(Model._rec_names_search or ([Model._rec_name] if Model._rec_name else []))
            if "seo_name" in Model._fields:
                search_fnames.add("seo_name")
            if search_fnames:
                name_domain = OR([[(name_field, "ilike", searches["search"])] for name_field in search_fnames])
                domains.append(name_domain)

        search_count = Model.search_count(AND(domains))
        pager = website.pager(
            url=f"/model/{page.name_slugified}",
            url_args=searches,
            total=search_count,
            page=page_number,
            step=self.pager_step,
            scope=5,
        )

        records = Model.search(AND(domains), limit=self.pager_step, offset=self.pager_step * (page_number - 1), order=searches["order"])

        render_context = {
            "order_by": searches["order"],
            "search": searches["search"],
            "search_count": search_count,
            "pager": pager,
            "records": records,
            "record_to_url": record_to_url,
            "layout_mode": layout_mode,
            "view_id": view.id,
            "main_object": page.sudo(), # The template reads some fields that are actually on view
        }
        return request.render(view.key, render_context)
