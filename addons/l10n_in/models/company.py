# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

import re

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_in_upi_id = fields.Char(string="UPI Id")

    l10n_in_gst_state_warning = fields.Json(compute="_compute_l10n_in_gst_state_warning")

    @api.depends('vat', 'state_id', 'country_code')
    def _compute_l10n_in_gst_state_warning(self):
        warnings = {}
        if self.vat and self.check_vat_in(self.vat) and self.country_code == "IN":
            if self.vat[:2] == "99":
                warnings['invalid_gst_type_on_overseas_invoice'] = {
                    'message': "As per GSTN the country should be other than India, so it's recommended to update it.",
                    'level': 'warning',
                }

            else:
                state_id = self.env['res.country.state'].search([('l10n_in_tin', '=', self.vat[:2])], limit=1)
                if state_id and state_id != self.state_id:
                    warnings['invalid_gst_type_on_overseas_invoice'] = {
                        'message': f"As per GSTN the state should be {state_id.name}, so it's recommended to update it.",
                        'level': 'warning',
                    }
        self.l10n_in_gst_state_warning = warnings

    def create(self, vals):
        res = super().create(vals)
        # Update Fiscal Positions for new branch
        res._update_l10n_in_fiscal_position()
        return res

    def write(self, vals):
        res = super().write(vals)
        if (vals.get('state_id') or vals.get('country_id')) and not self.env.context.get('delay_account_group_sync'):
            # Update Fiscal Positions for companies setting up state for the first time
            self._update_l10n_in_fiscal_position()
        return res

    def _update_l10n_in_fiscal_position(self):
        companies_need_update_fp = self.filtered(lambda c: c.parent_ids[0].chart_template == 'in')
        for company in companies_need_update_fp:
            ChartTemplate = self.env['account.chart.template'].with_company(company)
            fiscal_position_data = ChartTemplate._get_in_account_fiscal_position()
            ChartTemplate._load_data({'account.fiscal.position': fiscal_position_data})

    @api.onchange('vat')
    def onchange_vat(self):
        if self.vat and self.check_vat_in(self.vat):
            state_id = self.env['res.country.state'].search([('l10n_in_tin', '=', self.vat[:2])], limit=1)
            if state_id:
                self.state_id = state_id

    def check_vat_in(self, vat):
        # reference from https://www.gstzen.in/a/format-of-a-gst-number-gstin.html
        if vat and len(vat) == 15:
            all_gstin_re = [
                r'[0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[Zz1-9A-Ja-j]{1}[0-9a-zA-Z]{1}',      # Normal, Composite, Casual GSTIN
                r'[0-9]{4}[A-Z]{3}[0-9]{5}[UO]{1}[N][A-Z0-9]{1}',       # UN/ON Body GSTIN
                r'[0-9]{4}[a-zA-Z]{3}[0-9]{5}[N][R][0-9a-zA-Z]{1}',         # NRI GSTIN
                r'[0-9]{2}[a-zA-Z]{4}[a-zA-Z0-9]{1}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[DK]{1}[0-9a-zA-Z]{1}',         # TDS GSTIN
                r'[0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[C]{1}[0-9a-zA-Z]{1}'         # TCS GSTIN
            ]
            return any(re.compile(rx).match(vat) for rx in all_gstin_re)
        return False
