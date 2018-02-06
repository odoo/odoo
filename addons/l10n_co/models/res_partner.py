# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_co_document_type = fields.Selection([('rut', 'RUT'),
                                              ('id_card', 'Tarjeta de Identidad'),
                                              ('passport', 'Pasaporte'),
                                              ('foreign_id_card', 'Cedula de Extranjeria'),
                                              ('external_id', 'ID del Exterior')], string='Document Type',
                                             help='Indicates to what document the information in here belongs to.')
    l10n_co_verification_code = fields.Char(compute='_compute_verification_code', string='VC',
                                            help='Redundancy check to verify the vat number has been typed in correctly.')

    @api.depends('vat')
    def _compute_verification_code(self):
        multiplication_factors = [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]

        for partner in self.filtered(lambda partner: partner.vat and partner.country_id == self.env.ref('base.co') and
                                     len(partner.vat) <= len(multiplication_factors)):
            number = 0
            padded_vat = partner.vat

            while len(padded_vat) < len(multiplication_factors):
                padded_vat = '0' + padded_vat

            # if there is a single non-integer in vat the verification code should be False
            try:
                for index, vat_number in enumerate(padded_vat):
                    number += int(vat_number) * multiplication_factors[index]

                number %= 11

                if number < 2:
                    partner.l10n_co_verification_code = number
                else:
                    partner.l10n_co_verification_code = 11 - number
            except ValueError:
                partner.l10n_co_verification_code = False
