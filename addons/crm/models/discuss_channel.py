# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import html2plaintext


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _prepare_lead_create_values(self, partner, key):
        """Hook to prepare lead creation values from a discuss channel.

        :param partner: internal user partner (operator) that created the lead;
        :param key: operator input in chat ('/lead Lead about Product')
        """
        self.ensure_one()
        values = {
            "name": html2plaintext(key[5:]),
            "user_id": False,
            "team_id": False,
            "referred": partner.name,
        }
        return values
