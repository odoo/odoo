from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_tw_edi_require_paper_format = fields.Boolean(
        string="Require Paper Format",
        help="If checked, the partner requires paper format for ECPay e-invoices.",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_tw_edi_require_paper_format']
