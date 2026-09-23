from odoo import http
from odoo.http import request


class PortalRating(http.Controller):
    @http.route(
        ["/website/rating/comment"],
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def publish_rating_comment(self, rating_id, publisher_comment):
        try:
            rating_id = int(rating_id)
        except TypeError, ValueError:
            return {"error": request.env._("Invalid rating")}
        rating = request.env["rating.rating"].search_fetch(
            [("id", "=", rating_id)],
            ["publisher_comment", "publisher_id", "publisher_datetime"],
        )
        if not rating:
            return {"error": request.env._("Invalid rating")}
        rating.write({"publisher_comment": publisher_comment})
        return request.env["mail.message"]._portal_message_format_rating(
            rating.read(["publisher_comment", "publisher_id", "publisher_datetime"])[0]
        )
