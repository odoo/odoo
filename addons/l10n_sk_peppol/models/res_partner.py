from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_sk_dic = fields.Char(
        string="DIČ",
        compute='_compute_l10n_sk_dic',
        readonly=False,
        store=True,
        help="Slovak tax identification number assigned to all taxpayers",
    )

    @api.depends('vat')
    def _compute_l10n_sk_dic(self):
        for partner in self:
            if not partner.l10n_sk_dic and partner.vat:
                partner.l10n_sk_dic = partner.vat.upper().removeprefix('SK')

    def _peppol_eas_endpoint_depends(self):
        return super()._peppol_eas_endpoint_depends() + ['l10n_sk_dic']

    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_sk_dic']
