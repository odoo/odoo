from odoo import api, fields, models


class ResPartner(models.Model):
    """Exercises ``base_order``'s shared partner helpers on the test order type.

    sale and purchase both drive ``_compute_order_count`` /
    ``_add_order_statistics``, but neither carries a test for them, so the
    shared implementation is covered here instead of twice downstream.
    """

    _inherit = "res.partner"

    base_order_test_count = fields.Integer(
        string="Test Order Count",
        compute="_compute_base_order_test_count",
    )

    def _compute_base_order_test_count(self):
        self._update_order_count(
            "base.order.test",
            "base_order_test_count",
            "base.group_user",
            domain=self._get_base_order_test_domain_count(),
        )

    def _get_base_order_test_domain_count(self):
        """Extension point mirroring sale's/purchase's own domain hooks."""
        return []

    @api.model
    def _get_order_activity_sources(self):
        """Registers the test order type the way sale registers sale.order."""
        return super()._get_order_activity_sources() + [
            ("base.order.test", [("state", "=", "done")]),
        ]
