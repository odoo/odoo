from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_no_bronnoysund_number = fields.Char(
        string='Register of Legal Entities (Brønnøysund Register Center)',
        compute='_compute_l10n_no_bronnoysund_number',
        inverse='_inverse_l10n_no_bronnoysund_number',
    )

    @api.depends('additional_identifiers')
    def _compute_l10n_no_bronnoysund_number(self):
        for partner in self:
            partner.l10n_no_bronnoysund_number = partner._get_additional_identifier('NO_EN')

    def _inverse_l10n_no_bronnoysund_number(self):
        for partner in self:
            partner._set_additional_identifier('NO_EN', partner.l10n_no_bronnoysund_number)

    def _deduce_country_code(self):
        self.ensure_one()
        if self._get_additional_identifier('NO_EN'):
            return 'NO'
        return super()._deduce_country_code()
