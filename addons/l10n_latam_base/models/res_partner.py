# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_latam_identification_type_id = fields.Many2one('l10n_latam.identification.type',
        string="Identification Type", index='btree_not_null', auto_join=True,
        default=lambda self: self.env.ref('l10n_latam_base.it_vat', raise_if_not_found=False),
        inverse="_inverse_vat",  # To trigger the vat checking
        help="The type of identification")
    vat = fields.Char(string='Identification Number', help="Identification Number for selected type")

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_latam_identification_type_id']

    def _run_check_identification(self, validation='error'):
        return

    def _check_vat(self, validation='error'):
        partners_vat = self.filtered(lambda p:
            not p.l10n_latam_identification_type_id
            or p.l10n_latam_identification_type_id.is_vat
        )
        super(ResPartner, partners_vat)._check_vat(validation=validation)
        (self - partners_vat)._run_check_identification(validation=validation)

    @api.onchange('country_id')
    def _onchange_country_id(self):
        country = self.country_id or self.company_id.account_fiscal_country_id or self.env.company.account_fiscal_country_id
        identification_type = self.l10n_latam_identification_type_id
        if not identification_type or (identification_type.country_id != country):
            self.l10n_latam_identification_type_id = self.env['l10n_latam.identification.type'].search(
                [('country_id', '=', country.id), ('is_vat', '=', True)], limit=1) or self.env.ref(
                    'l10n_latam_base.it_vat', raise_if_not_found=False)

    @api.onchange('vat', 'country_id', 'l10n_latam_identification_type_id')
    def _onchange_vat(self):
        super()._onchange_vat()

    def _get_frontend_writable_fields(self):
        frontend_writable_fields = super()._get_frontend_writable_fields()
        frontend_writable_fields.add('l10n_latam_identification_type_id')

        return frontend_writable_fields
