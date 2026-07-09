from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_l10n_pk_edi_pos_enabled = fields.Boolean(related='pos_config_id.l10n_pk_edi_pos_enabled', readonly=False)
    pos_l10n_pk_edi_pos_identifier = fields.Char(related='pos_config_id.l10n_pk_edi_pos_identifier', readonly=False)
    pos_l10n_pk_edi_pos_test_identifier = fields.Char(related='pos_config_id.l10n_pk_edi_pos_test_identifier', readonly=False)
    pos_l10n_pk_edi_pos_token = fields.Char(related='pos_config_id.l10n_pk_edi_pos_token', readonly=False)
    pos_l10n_pk_edi_pos_charge_service_fee = fields.Boolean(related='pos_config_id.l10n_pk_edi_pos_charge_service_fee', readonly=False)
    pos_l10n_pk_edi_pos_service_fee_product_id = fields.Many2one(related='pos_config_id.l10n_pk_edi_pos_service_fee_product_id', readonly=False)
    pos_l10n_pk_edi_pos_sandbox = fields.Boolean(related='pos_config_id.l10n_pk_edi_pos_sandbox', readonly=False)
