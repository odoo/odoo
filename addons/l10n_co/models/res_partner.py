# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_co_document_type = fields.Selection([('rut', 'NIT'),
                                              ('id_document', 'Cédula'),
                                              ('id_card', 'Tarjeta de Identidad'),
                                              ('passport', 'Pasaporte'),
                                              ('foreign_id_card', 'Cédula Extranjera'),
                                              ('external_id', 'ID del Exterior'),
                                              ('diplomatic_card', 'Carné Diplomatico'),
                                              ('residence_document', 'Salvoconducto de Permanencia'),
                                              ('civil_registration', 'Registro Civil'),
                                              ('national_citizen_id', 'Cédula de ciudadanía')], string='Document Type',
                                             help='Indicates to what document the information in here belongs to.')

    @api.constrains('vat', 'country_id', 'l10n_co_document_type')
    def check_vat(self):
        # check_vat is implemented by base_vat which this localization
        # doesn't directly depend on. It is however automatically
        # installed for Colombia.
        if self.sudo().env.ref('base.module_base_vat').state == 'installed':
            # don't check Colombian partners unless they have RUT (= Colombian VAT) set as document type
            self = self.filtered(lambda partner: partner.country_id != self.env.ref('base.co') or\
                                                 partner.l10n_co_document_type == 'rut')
            return super(ResPartner, self).check_vat()
        else:
            return True
