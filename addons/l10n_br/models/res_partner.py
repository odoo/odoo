from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_br_ie_code = fields.Char(
        string="IE",
        help="State Tax Identification Number. Should contain 9-14 digits.",
    )
    l10n_br_im_code = fields.Char(
        string="IM",
        help="Municipal Tax Identification Number",
    )
    l10n_br_isuf_code = fields.Char(
        string="SUFRAMA code",
        help="SUFRAMA registration number.",
    )

    def _get_fields_frontend_writable(self):
        frontend_writable_fields = super()._get_fields_frontend_writable()
        frontend_writable_fields.update(
            {"city_id", "street_number", "street_name", "street_number2"}
        )

        return frontend_writable_fields
