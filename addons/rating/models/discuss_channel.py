# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _delete_extra(self):
        yield from super()._delete_extra()
        yield self.env["rating.rating"].search(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)],
        )
