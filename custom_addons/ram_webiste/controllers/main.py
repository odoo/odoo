from odoo import http, _
from odoo.http import request


class RamWebsiteController(http.Controller):
    @http.route(
        ["/ram/contact"],
        type="http",
        auth="public",
        website=True,
        methods=["GET", "POST"],
        csrf=True,
        sitemap=True,
    )
    def ram_contact(self, **post):
        if request.httprequest.method == "POST":
            name = (post.get("name") or "").strip()
            email = (post.get("email") or "").strip()
            phone = (post.get("phone") or "").strip()
            message = (post.get("message") or "").strip()

            # Minimal validation: keep UX smooth; admin can follow up from CRM.
            if name and (email or phone) and message:
                request.env["crm.lead"].sudo().create(
                    {
                        "name": _("Website Contact: %s") % name,
                        "contact_name": name,
                        "email_from": email,
                        "phone": phone,
                        "description": message,
                        "type": "lead",
                    }
                )
                return request.render("ram_webiste.ram_contact_thank_you", {})

            return request.render(
                "ram_webiste.ram_contact_page",
                {
                    "error": _(
                        "Please fill in your name, a way to reach you (email or phone), and your message."
                    ),
                    "values": {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "message": message,
                    },
                },
            )

        return request.render("ram_webiste.ram_contact_page", {"values": {}})

    @http.route(
        ["/ram/reviews"],
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
        readonly=True,
    )
    def ram_reviews_json(self, limit=12):
        reviews = (
            request.env["ram.website.review"]
            .sudo()
            .search([("is_published", "=", True)], order="sequence asc, id desc", limit=int(limit or 12))
        )
        return [
            {
                "id": r.id,
                "author_name": r.author_name,
                "rating": r.rating,
                "content": r.content,
                "source": r.source,
                "review_url": r.review_url,
                "create_date": r.create_date.isoformat() if r.create_date else None,
            }
            for r in reviews
        ]

