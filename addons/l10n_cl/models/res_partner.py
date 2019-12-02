# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import stdnum
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    _sii_taxpayer_types = [
        ('1', _('VAT Affected (1st Category)')),
        ('2', _('Fees Receipt Issuer (2nd category)')),
        ('3', _('End Consumer')),
        ('4', _('Foreigner')),
    ]

    l10n_cl_sii_taxpayer_type = fields.Selection(
        _sii_taxpayer_types, 'Taxpayer Type', index=True,
        help='1 - VAT Affected (1st Category) (Most of the cases)\n'
             '2 - Fees Receipt Issuer (Applies to suppliers who issue fees receipt)\n'
             '3 - End consumer (only receipts)\n'
             '4 - Foreigner')

    def _format_vat_cl(self, values):
        identification_types = [self.env.ref('l10n_latam_base.it_vat').id, self.env.ref('l10n_cl.it_RUT').id,
                                self.env.ref('l10n_cl.it_RUN').id]
        partner_country_is_chile = (values.get('country_id') == self.env.ref('base.cl').id) or (
                    values.get('l10n_latam_identification_type_id') and
                    self.env['l10n_latam.identification.type'].browse(
                        values.get('l10n_latam_identification_type_id')).country_id == self.env.ref('base.cl'))
        if partner_country_is_chile and \
                values.get('l10n_latam_identification_type_id') in identification_types and values.get('vat'):
            return stdnum.util.get_cc_module('cl', 'vat').format(values['vat']).replace('.', '').replace(
                'CL', '').upper()
        else:
            return values['vat']

    @api.model
    def create(self, values):
        if values.get('vat'):
            values['vat'] = self._format_vat_cl(values)
        return super().create(values)

    def write(self, values):
        for record in self:
            vat_values = {
                'vat': values.get('vat', record.vat),
                'l10n_latam_identification_type_id': values.get(
                    'l10n_latam_identification_type_id', record.l10n_latam_identification_type_id.id),
                'country_id': values.get('country_id', record.country_id.id)
            }
            values['vat'] = self._format_vat_cl(vat_values)
        return super().write(values)
