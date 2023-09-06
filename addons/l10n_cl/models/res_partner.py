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
        _sii_taxpayer_types, 'Taxpayer Type', index='btree_not_null',
        help='1 - VAT Affected (1st Category) (Most of the cases)\n'
             '2 - Fees Receipt Issuer (Applies to suppliers who issue fees receipt)\n'
             '3 - End consumer (only receipts)\n'
             '4 - Foreigner')
    l10n_cl_activity_description = fields.Char(string='Activity Description', help="Chile: Economic activity.")

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_cl_sii_taxpayer_type']

    def _format_vat_cl(self, values):
        identification_types = [self.env.ref('l10n_latam_base.it_vat').id, self.env.ref('l10n_cl.it_RUT').id,
                                self.env.ref('l10n_cl.it_RUN').id]
        country = self.env["res.country"].browse(values.get('country_id'))
        identification_type = self.env['l10n_latam.identification.type'].browse(
            values.get('l10n_latam_identification_type_id')
        )
        partner_country_is_chile = country.code == "CL" or identification_type.country_id.code == "CL"
        if partner_country_is_chile and \
                values.get('l10n_latam_identification_type_id') in identification_types and values.get('vat'):
            return stdnum.util.get_cc_module('cl', 'vat').format(values['vat']).replace('.', '').replace(
                'CL', '').upper()
        else:
            return values['vat']

    def _format_dotted_vat_cl(self, vat):
        vat_l = vat.split('-')
        n_vat, n_dv = vat_l[0], vat_l[1]
        return '%s-%s' % (format(int(n_vat), ',d').replace(',', '.'), n_dv)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('vat'):
                vals['vat'] = self._format_vat_cl(vals)
        return super().create(vals_list)

    def write(self, values):
        if any(field in values for field in ['vat', 'l10n_latam_identification_type_id', 'country_id']):
            for record in self:
                vat_values = {
                    'vat': values.get('vat', record.vat),
                    'l10n_latam_identification_type_id': values.get(
                        'l10n_latam_identification_type_id', record.l10n_latam_identification_type_id.id),
                    'country_id': values.get('country_id', record.country_id.id)
                }
                values['vat'] = self._format_vat_cl(vat_values)
        return super().write(values)
