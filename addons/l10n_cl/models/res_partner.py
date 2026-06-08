# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_cl_sii_taxpayer_type = fields.Selection(
        [
            ('1', 'VAT Affected (1st Category)'),
            ('2', 'Fees Receipt Issuer (2nd category)'),
            ('3', 'End Consumer'),
            ('4', 'Foreigner'),
        ],
        string='Taxpayer Type',
        index='btree_not_null',
        help='1 - VAT Affected (1st Category) (Most of the cases)\n'
             '2 - Fees Receipt Issuer (Applies to suppliers who issue fees receipt)\n'
             '3 - End consumer (only receipts)\n'
             '4 - Foreigner')
    l10n_cl_activity_description = fields.Char(string='Activity Description', help="Chile: Economic activity.")

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_cl_sii_taxpayer_type']

    def _run_check_identification(self, validation='error'):
        """ We format the RUN thing (actually, it could just use the parent method)"""
        l10n_cl_partners = self.filtered(lambda p: p.vat and len(p.vat) > 2 and p.country_code == 'CL')
        if l10n_cl_partners:
            identification_types = [self.env.ref('l10n_cl.it_RUN').id]
            for partner in l10n_cl_partners.filtered(lambda p: p.l10n_latam_identification_type_id.id in identification_types):
                partner.vat = partner.format_vat_cl(partner.vat)

                if validation == 'error':
                    if not partner._check_vat_number('CL', partner.vat):
                        raise ValidationError(_('The format of your RUN is not valid.  It should be like 76086428-5.'))

        return super(ResPartner, self - l10n_cl_partners)._run_check_identification(validation=validation)

    def _format_dotted_vat_cl(self, vat):
        vat_l = vat.split('-')
        n_vat, n_dv = vat_l[0], vat_l[1]
        return '%s-%s' % (format(int(n_vat), ',d').replace(',', '.'), n_dv)
