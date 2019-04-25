##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
from ast import literal_eval


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    l10n_ar_unique_id_numbers = fields.Boolean(
        string="Use unique Identification Numbers",
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        l10n_ar_unique_id_numbers = literal_eval(
            self.env["ir.config_parameter"].get_param(
                "l10n_ar_base.unique_id_numbers", default='False'))
        res.update(
            l10n_ar_unique_id_numbers=l10n_ar_unique_id_numbers,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param(
            "l10n_ar_base.unique_id_numbers",
            repr(self.l10n_ar_unique_id_numbers))
