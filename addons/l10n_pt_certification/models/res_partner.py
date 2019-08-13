# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # 3.3.3, 3.3.4
    @api.multi
    def write(self, vals):
        for partner in self:
            if self.env['account.move'].search_count([('partner_id', '=', partner.id)]):
                if 'vat' in vals and partner.vat and partner.vat != '999999990':
                    raise ValidationError(_("You can't not modify the VAT number of a partner with invoices."))
                if 'name' in vals and not partner.vat:
                    raise ValidationError(_("You can't modify the name of a partner without a VAT number and with "
                                            "created documents."))
        return super(ResPartner, self).write(vals)
