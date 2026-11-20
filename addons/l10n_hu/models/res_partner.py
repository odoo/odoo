from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_hu_eu_vat = fields.Char(compute='_compute_l10n_hu_eu_vat')

    @api.depends('vat')
    def _compute_l10n_hu_eu_vat(self):
        for partner in self:
            if partner.vat and partner.vat != '/':
                partner.l10n_hu_eu_vat = partner._convert_hu_local_to_eu_vat(partner.vat)
            else:
                partner.l10n_hu_eu_vat = False

    @api.depends_context('l10n_hu_postal_address')
    def _compute_address(self):
        super()._compute_address()

    @api.depends_context('l10n_hu_postal_address')
    def _compute_display_name(self):
        super()._compute_display_name()

    def _get_address_format(self):
        # Magyar Posta: settlement, street and house number, then the postcode on its own last line.
        if self.env.context.get('l10n_hu_postal_address') and self.country_id.code == 'HU':
            address_format = "%(city)s\n%(street)s\n%(street2)s\n%(zip)s"
            if self.env.company.country_code != 'HU':
                address_format += "\n%(country_name)s"
            return address_format
        return super()._get_address_format()
