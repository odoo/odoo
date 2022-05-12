from odoo import models, _
from odoo.exceptions import UserError


class Partner(models.Model):
    _inherit = 'res.partner'

    def write(self, vals):
        if self.env.company.account_fiscal_country_id.code != 'PT':
            return super().write(vals)
        for partner in self:
            if 'vat' in vals and partner.vat:
                if self.env['account.move'].search_count([('partner_id', '=', partner.id)]):
                    raise UserError(_("You cannot change the VAT number of a partner that already has invoices."))
            if 'name' in vals and not partner.vat:
                if self.env['account.move'].search_count([('partner_id', '=', partner.id)]):
                    raise UserError(_("You cannot change the name of a partner that already has invoices but no VAT number.\n To remove this restriction, you can add the VAT number of the partner."))
        return super().write(vals)
