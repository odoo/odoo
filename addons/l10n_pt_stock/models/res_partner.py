import re

from odoo import _, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def write(self, values):
        for partner in self:
            if (
                values.get('vat')
                and partner.company_id and partner.company_id.account_fiscal_country_id.code == 'PT'
                and partner.vat
                and re.sub(r"[^0-9]", "", partner.vat) != "999999990"
            ):
                if self.env['stock.picking'].search_count([
                    ('partner_id', '=', partner.id),
                    ('state', 'in', ('done', 'cancel')),
                ]):
                    raise UserError(_("You cannot change the VAT number of a partner that already has issued documents"))
        return super().write(values)
