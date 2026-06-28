from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ca_pst = fields.Char(related='partner_id.l10n_ca_pst', string='PST Number', store=False, readonly=False)

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state_id'):
            self._update_l10n_ca_fiscal_position()
        return res

    def _update_l10n_ca_fiscal_position(self):
        """ Put the local fiscal position first, so that domestic_fiscal_position_id is set right. """
        for company in self.filtered(lambda c: c.root_id.chart_template == 'ca_2023'):
            local_fp = self.env['account.fiscal.position'].with_company(company).search([('state_ids', 'in', company.state_id.id)], limit=1)
            if not local_fp:
                continue

            ca_fps = company.fiscal_position_ids.filtered(lambda fp: fp.country_id.code == 'CA')
            local_fp.sequence = min(ca_fps.mapped('sequence')) - 1


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    l10n_ca_pst = fields.Char(related='company_id.l10n_ca_pst', readonly=True)
    account_fiscal_country_id = fields.Many2one(related="company_id.account_fiscal_country_id", readonly=True)
