# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

FINANCIAL_STATEMENT_TYPE_SELECTION = [
    ("01", "01 - SUPERINTENDENCY OF THE STOCK MARKET - MISCELLANEOUS SECTOR - INDIVIDUAL"),
    ("02", "02 - SUPERINTENDENCY OF THE SECURITIES MARKET - INSURANCE SECTOR - INDIVIDUAL"),
    ("03", "03 - SUPERINTENDENCY OF THE SECURITIES MARKET - BANKING AND FINANCIAL SECTOR - INDIVIDUAL"),
    ("04", "04 - SUPERINTENDENCY OF THE STOCK MARKET - PENSION FUND ADMINISTRATORS (AFP)"),
    ("05", "05 - SUPERINTENDENCY OF THE STOCK MARKET - INTERMEDIATION AGENTS"),
    ("06", "06 - SUPERINTENDENCY OF THE STOCK MARKET - INVESTMENT FUNDS"),
    ("07", "07 - SUPERINTENDENCY OF THE SECURITIES MARKET - ASSETS IN TRUSTS"),
    ("08", "08 - SUPERINTENDENCY OF THE STOCK MARKET - ICLV"),
    ("09", "09 - OTHERS NOT CONSIDERED IN THE PREVIOUS"),
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pe_financial_statement_type = fields.Selection(selection=FINANCIAL_STATEMENT_TYPE_SELECTION, string="PLE Type of Financial Statement")
    l10n_pe_shareholder_ids = fields.One2many('l10n_pe_reports_lib.shareholder', 'company_id', string='Shareholders')

    @api.constrains('l10n_pe_shareholder_ids')
    def _check_l10n_pe_shareholder_percentage(self):
        for record in self:
            if sum(shareholder.shares_percentage for shareholder in record.l10n_pe_shareholder_ids) > 100.0:
                raise ValidationError(_('Sum of shareholder share percentages should not exceed 100%%.'))


class L10nPEShareholder(models.Model):
    _name = 'l10n_pe_reports_lib.shareholder'
    _description = 'Shareholder breakdown for Peruvian reports'

    company_id = fields.Many2one('res.company', string="Company", required=True)
    partner_id = fields.Many2one('res.partner', string="Partner")
    participation_type_code = fields.Selection(
        selection=[
            ("01", "01 - SHARES WITH RIGHT TO VOTE"),
            ("02", "02 - SHARES WITHOUT RIGHT TO VOTE"),
            ("03", "03 - SOCIAL INTERESTS"),
            ("04", "04 - OTHER"),
        ],
        string="Participation Type Code",
    )
    shares_qty = fields.Integer(string="Shares Quantity")
    shares_percentage = fields.Float(string="Shares Percentage")
    shares_date = fields.Date(string="Date of incorporation")

    @api.constrains('shares_percentage')
    def _check_shares_percentage(self):
        for record in self:
            if record.shares_percentage > 100.0 or record.shares_percentage <= 0.0:
                raise ValidationError(_('Share percentages should be between 0%% and  100%%.'))
