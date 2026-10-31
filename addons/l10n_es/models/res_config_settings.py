from odoo import fields, models
from odoo.tools import SQL
from odoo.tools.sql import column_exists, create_column


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_es_simplified_invoice_limit = fields.Float(
        related='company_id.l10n_es_simplified_invoice_limit',
        readonly=False,
    )
    l10n_es_special_vat_regime = fields.Selection(
        related='company_id.l10n_es_special_vat_regime',
        readonly=False,
    )
    module_l10n_es_edi_verifactu = fields.Boolean('Veri*Factu')
    module_l10n_es_edi_sii = fields.Boolean('SII')
    module_l10n_es_edi_tbai = fields.Boolean('TicketBai')
    module_l10n_es_website_sale = fields.Boolean('eCommerce')

    def set_values(self):
        super().set_values()
        # This way, once l10n_es_edi_verifactu is installed, the field is already set for the
        # company the user was on, instead of needing to tick it again after the install reload
        # (where there's no company context left to know which one that was).
        if self.module_l10n_es_edi_verifactu and not column_exists(self.env.cr, "res_company", "l10n_es_edi_verifactu_required"):
            create_column(self.env.cr, "res_company", "l10n_es_edi_verifactu_required", "bool")
            self.env.cr.execute(SQL(
                "UPDATE res_company SET l10n_es_edi_verifactu_required = true WHERE id = %s",
                self.company_id.id,
            ))
