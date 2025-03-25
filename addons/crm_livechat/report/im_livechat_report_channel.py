# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class Im_LivechatReportChannel(models.Model):
    _inherit = "im_livechat.report.channel"

    leads_created = fields.Integer("Leads created", aggregator="sum", readonly=True)

    def _select(self) -> SQL:
        return SQL("%s, count(distinct crm_lead.id) as leads_created", super()._select())

    def _from(self) -> SQL:
        return SQL("%s LEFT JOIN crm_lead ON (crm_lead.origin_channel_id = C.id)", super()._from())
