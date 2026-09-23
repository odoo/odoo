from odoo import fields
from odoo.http import request, route

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class CustomerPortalLoyalty(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if not counters:
            # we want those data to be added to the /my/home page only, and always computed
            values["cards_per_programs"] = dict(
                request.env["loyalty.card"]
                .sudo()
                ._read_group(
                    domain=[
                        ("partner_id", "=", request.env.user.partner_id.id),
                        ("program_id.active", "=", True),
                        ("program_id.program_type", "in", ["loyalty", "ewallet"]),
                        "|",
                        ("expiration_date", ">=", fields.Date().today()),
                        ("expiration_date", "=", False),
                    ],
                    groupby=["program_id"],
                    aggregates=["id:recordset"],
                )
            )

        return values

    def _get_own_loyalty_card(self, card_id):
        """Return the visitor's own card `card_id`, or an empty recordset.

        Both loyalty routes are `auth='user'` and read through `sudo()`; this is the
        single place that turns a URL id back into a card the visitor may see.
        """
        return (
            request.env["loyalty.card"]
            .sudo()
            .search(
                [
                    ("id", "=", card_id),
                    ("partner_id", "=", request.env.user.partner_id.id),
                ]
            )
        )

    def _get_loyalty_searchbar_sortings(self):
        return {
            "date": {"label": request.env._("Date"), "order": "create_date desc"},
            "used": {"label": request.env._("Used"), "order": "used desc"},
            "description": {
                "label": request.env._("Description"),
                "order": "description desc",
            },
            "issued": {"label": request.env._("Issued"), "order": "issued desc"},
        }

    @route(
        [
            "/my/loyalty_card/<int:card_id>/history",
            "/my/loyalty_card/<int:card_id>/history/page/<int:page>",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_loyalty_card_history(self, card_id, page=1, sortby="date", **kw):
        card_sudo = self._get_own_loyalty_card(card_id)
        if not card_sudo:
            return request.redirect("/my")

        LoyaltyHistorySudo = request.env["loyalty.history"].sudo()
        searchbar_sortings = self._get_loyalty_searchbar_sortings()
        # The route signature's `sortby='date'` only covers an *absent* param;
        # a supplied unknown key reached this indexing as a KeyError (HTTP 500).
        sortby = self._resolve_searchbar_option(searchbar_sortings, sortby, "date")
        order = searchbar_sortings[sortby]["order"]
        # The card is already the visitor's own, so ownership is not restated here:
        # a second condition that the count above does not carry would page over one
        # set and count another.
        history_domain = [("card_id", "=", card_sudo.id)]
        pager = portal_pager(
            url="/my/loyalty_card/<int:card_id>/history",
            url_args={"sortby": sortby, "card_id": card_id},
            total=LoyaltyHistorySudo.search_count(history_domain),
            page=page,
            step=self._items_per_page,
        )
        history_lines = LoyaltyHistorySudo.search(
            domain=history_domain,
            order=order,
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        values = {
            "pager": pager,
            "searchbar_sortings": searchbar_sortings,
            "page_name": "loyalty_history",
            "sortby": sortby,
            "history_lines": history_lines,
        }

        return request.render("loyalty.loyalty_card_history_template", values)

    @route("/my/loyalty_card/<int:card_id>/values", type="jsonrpc", auth="user")
    def portal_get_card_history_values(self, card_id):
        """Retrieve card history values for portal card dialog.

        :param int card_id: The ID of the loyalty card.
        :return: The card, its program, its latest history, its reachable
                 rewards and its program type image path.
        :rtype: dict
        """
        card_sudo = self._get_own_loyalty_card(card_id)
        if not card_sudo:
            return {}

        program_type = card_sudo.program_id.program_type
        rewards = (
            request.env["loyalty.reward"]
            .sudo()
            .search(
                [
                    ("program_id", "=", card_sudo.program_id.id),
                    ("required_points", "<=", card_sudo.points),
                ],
                order="required_points desc",
                limit=3,
            )
        )
        return {
            "card": {
                "id": card_sudo.id,
                "points_display": card_sudo.points_display,
                "expiration_date": card_sudo.expiration_date,
                "code": card_sudo.code,
            },
            "program": {
                "program_name": card_sudo.program_id.name,
                "program_type": program_type,
            },
            "history_lines": [
                {
                    "order_id": line.order_id,
                    "description": line.description,
                    "order_portal_url": line.order_portal_url,
                    "points": f"{'-' if line.issued < line.used else '+'}"
                    f"{card_sudo._format_points(abs(line.issued - line.used))}",
                }
                for line in request.env["loyalty.history"]
                .sudo()
                .search(
                    [("card_id", "=", card_sudo.id)],
                    limit=5,
                )
            ],
            "rewards": [
                {
                    "description": reward.description,
                    "points": card_sudo._format_points(reward.required_points),
                }
                for reward in rewards
            ],
            # Only 'loyalty' and 'ewallet' ship art under static/src/img/;
            # other program types' art lives under static/img/ (no 'src/').
            "img_path": (
                f"/loyalty/static/src/img/{program_type}.svg"
                if program_type in ("loyalty", "ewallet")
                else False
            ),
        }
