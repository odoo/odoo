# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class Im_LivechatReportChannel(models.Model):
    _inherit = "im_livechat.report.channel"

    leads_created = fields.Integer("Leads created", aggregator="sum", readonly=True)

    def _select(self) -> SQL:
        return SQL("%s, crm_lead_data.leads_created AS leads_created", super()._select())

    def _from(self) -> SQL:
        return SQL(
            """%s
            LEFT JOIN LATERAL
                (
                    SELECT count(*) AS leads_created
                      FROM crm_lead
                     WHERE crm_lead.origin_channel_id = C.id
                ) AS crm_lead_data ON TRUE
            """,
            super()._from(),
        )
