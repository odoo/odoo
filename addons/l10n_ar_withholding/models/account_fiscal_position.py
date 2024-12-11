from odoo import models, fields


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    l10n_ar_tax_ids = fields.One2many('account.fiscal.position.l10n_ar_tax', 'fiscal_position_id')

    def _l10n_ar_add_taxes(self, partner, company, date):
        # TODO deberiamos unificar mucho de este codigo con _get_tax_domain, _compute_withholdings y _check_tax_group_overlap
        self.ensure_one()
        taxes = self.env['account.tax']
        for fp_tax in self.l10n_ar_tax_ids:
            domain = self.env['l10n_ar.partner.tax']._check_company_domain(company)
            domain += [('tax_id.tax_group_id', '=', fp_tax.default_tax_id.tax_group_id.id)]
            domain += [
                '|', ('from_date', '<=', date), ('from_date', '=', False),
                '|', ('to_date', '>=', date), ('to_date', '=', False),
            ]
            partner_tax = partner.l10n_ar_partner_perception_ids.filtered_domain(domain).mapped('tax_id')
            # agregamos taxes para grupos de impuestos que no estaban seteados en el partner
            if not partner_tax:
                partner_tax = fp_tax._get_missing_taxes(partner, date)
            taxes |= partner_tax
        return taxes
