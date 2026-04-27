# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_nl_reports_sbr_icp_last_sent_date_to = fields.Date(
        'Last Date Sent (ICP)',
        help="Stores the date of the end of the last period submitted to the Digipoort Services for ICP",
        readonly=True
    )
