# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import stdnum.br.cpf

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_br_ie_code = fields.Char(string="IE", help="State Tax Identification Number. Should contain 9-14 digits.")
    l10n_br_im_code = fields.Char(string="IM", help="Municipal Tax Identification Number")
    l10n_br_isuf_code = fields.Char(string="SUFRAMA code", help="SUFRAMA registration number.")

    @api.constrains('vat', 'l10n_latam_identification_type_id')
    def check_cpf(self):
        for partner in self.filtered(lambda partner: partner.l10n_latam_identification_type_id == self.env.ref('l10n_br.cpf')):
            if partner.vat and not stdnum.br.cpf.is_valid(partner.vat) and not stdnum.br.cnpj.is_valid(partner.vat):
                raise ValidationError(_('CPF/CNPJ number %s for %s is not valid.') % (partner.vat, partner.display_name))
