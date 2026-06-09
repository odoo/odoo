import json
import random
import time

from odoo import http


class WebsiteContact(http.Controller):
    @http.route(
        "/website/contact",
        type="http",
        auth="public",
        methods=["POST"],
        multilang=False,
        readonly=True,
        csrf=False,
    )
    def website_contact(self, name=None, **kwargs):
        time.sleep(2)
        should_fail = random.randint(1, 100) % 2 == 0
        if should_fail:
            raise ValueError(
                "You got an even number, so you can't really contact them. goodbye."
            )

        return json.dumps({"status": "success"})
