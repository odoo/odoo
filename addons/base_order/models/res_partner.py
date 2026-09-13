from odoo import api, fields, models
from odoo.fields import Domain

_DAYS_NO_ORDER_SENTINEL = 9999


class ResPartner(models.Model):
    _inherit = "res.partner"

    recent_orders_count = fields.Integer(
        string="Recent Orders",
        help="Number of orders this partner placed within the order cycle "
        "configured on the company.",
        compute="_compute_recent_orders_count",
    )
    days_since_last_order = fields.Integer(
        help="Number of days since this partner's last order.",
        compute="_compute_days_since_last_order",
    )

    def _compute_order_count(self, order_model, count_field, group, domain=None):
        self[count_field] = 0
        if not self.env.user.has_group(group):
            return

        all_partners = self.with_context(active_test=False).search_fetch(
            [("id", "child_of", self.ids)],
            ["parent_id"],
        )
        order_groups = (
            self.env[order_model]
            .sudo()
            ._read_group(
                domain=Domain.AND(
                    [
                        domain or [],
                        [("partner_id", "in", all_partners.ids)],
                    ],
                ),
                groupby=["partner_id"],
                aggregates=["__count"],
            )
        )
        self_ids = set(self._ids)

        for partner, count in order_groups:
            while partner:
                if partner.id in self_ids:
                    partner[count_field] += count
                partner = partner.parent_id

    def _add_order_statistics(
        self,
        data_list,
        count_field,
        group,
        icon_class,
        label,
        tag_class,
    ):
        if not self.env.user.has_group(group):
            return data_list
        for partner in self.filtered(count_field):
            data_list[partner.id].append(
                {
                    "iconClass": icon_class,
                    "value": partner[count_field],
                    "label": label,
                    "tagClass": tag_class,
                },
            )
        return data_list

    @api.model
    def _get_order_activity_sources(self):
        return []

    def _get_order_activity_partners(self):
        return self

    def _get_domain_order_activity_scope(self):
        return [("company_id", "=", self.env.company.id)]

    def _get_readable_order_activity_sources(self, sources):
        return [
            (order_model, domain)
            for order_model, domain in sources
            if self.env[order_model].has_access("read")
        ]

    @api.depends_context("company", "uid")
    def _compute_recent_orders_count(self):
        self.recent_orders_count = 0
        partners = self._get_order_activity_partners()
        sources = self._get_readable_order_activity_sources(
            self._get_order_activity_sources(),
        )
        if not partners or not sources:
            return

        cutoff_date = self.env.company._get_order_cycle_cutoff_date()
        counts = {}
        for order_model, domain in sources:
            order_groups = (
                self.env[order_model]
                .sudo()
                ._read_group(  # pylint: disable=n-plus-one-query
                    domain=Domain.AND(
                        [
                            domain,
                            self._get_domain_order_activity_scope(),
                            [
                                ("partner_id", "in", partners.ids),
                                ("date_order", ">=", cutoff_date),
                            ],
                        ],
                    ),
                    groupby=["partner_id"],
                    aggregates=["__count"],
                )
            )
            for partner, count in order_groups:
                counts[partner.id] = counts.get(partner.id, 0) + count

        for partner in partners:
            partner.recent_orders_count = counts.get(partner.id, 0)

    @api.depends_context("company", "uid")
    def _compute_days_since_last_order(self):
        self.days_since_last_order = 0
        partners = self._get_order_activity_partners()
        sources = self._get_readable_order_activity_sources(
            self._get_order_activity_sources(),
        )
        if not partners or not sources:
            return

        last_dates = {}
        for order_model, domain in sources:
            order_groups = (
                self.env[order_model]
                .sudo()
                ._read_group(  # pylint: disable=n-plus-one-query
                    domain=Domain.AND(
                        [
                            domain,
                            self._get_domain_order_activity_scope(),
                            [("partner_id", "in", partners.ids)],
                        ],
                    ),
                    groupby=["partner_id"],
                    aggregates=["date_order:max"],
                )
            )
            for partner, last_date in order_groups:
                previous = last_dates.get(partner.id)
                if previous is None or last_date > previous:
                    last_dates[partner.id] = last_date

        today = fields.Date.today()
        for partner in partners:
            last_date = last_dates.get(partner.id)
            partner.days_since_last_order = (
                (today - last_date.date()).days
                if last_date
                else _DAYS_NO_ORDER_SENTINEL
            )
