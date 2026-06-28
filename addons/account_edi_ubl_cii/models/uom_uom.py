from odoo import fields, models, api


class UomUom(models.Model):
    _inherit = "uom.uom"

    unece_code = fields.Char(
        "UN/ECE Code",
        copy=False,
        help="The code element for units of measurement (UoM) as specified by UN/ECE",
    )
    is_unece_code_supported = fields.Boolean(compute="_compute_is_unece_code_supported")

    _unece_code_unique = models.Constraint(
        'unique (unece_code)',
        'The UN/ECE code already exists!',
    )

    def _sanitize_vals(self, vals):
        if vals.get('unece_code'):
            vals['unece_code'] = vals['unece_code'].upper()
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        return super().create([self._sanitize_vals(vals) for vals in vals_list])

    def write(self, vals):
        return super().write(self._sanitize_vals(vals))

    def _compute_is_unece_code_supported(self):
        for uom in self:
            uom.is_unece_code_supported = uom.env.company.account_fiscal_country_id.code in [
                "AL", "AD", "AM", "AT", "AZ", "BY", "BE", "BA", "BG", "CA", "HR", "CY", "CZ",
                "DK", "EE", "FI", "FR", "GE", "DE", "GR", "HU", "IS", "IE", "IL", "IT", "KZ",
                "KG", "LV", "LI", "LT", "LU", "MT", "MD", "MC", "ME", "NL", "MK", "NO", "PL",
                "PT", "RO", "RU", "SM", "RS", "SK", "SI", "ES", "SE", "CH", "TJ", "TR", "TM",
                "UA", "GB", "US", "UZ", "JO", "JP", "AU", "NZ", "MY", "SA", "SG",
            ]

    def _get_unece_code(self):
        return self.unece_code or super()._get_unece_code()

    @api.model
    def _get_uom_from_unece_code(self, unece_code):
        uom = self.env['uom.uom'].with_context(active_test=False).search([('unece_code', '=', unece_code.upper())], limit=1)
        return uom or super()._get_uom_from_unece_code(unece_code)
