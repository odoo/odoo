# @ 2016 Kmee - www.kmee.com.br
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    allow_cnpj_multi_ie = fields.Boolean(
        string="Multiple partners with the same CNPJ",
        config_parameter="l10n_br_base.allow_cnpj_multi_ie",
        default=False,
    )

    disable_cpf_cnpj_validation = fields.Boolean(
        "Disable CPF and CNPJ validation",
        config_parameter="l10n_br_base.disable_cpf_cnpj_validation",
        default=False,
    )

    disable_ie_validation = fields.Boolean(
        "Disable IE validation",
        config_parameter="l10n_br_base.disable_ie_validation",
        default=False,
    )

    module_l10n_br_zip = fields.Boolean(string="Use Brazilian postal service API")
