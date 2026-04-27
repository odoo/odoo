from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = ['pos.payment.method']

    l10n_co_edi_pos_payment_option_id = fields.Many2one(comodel_name='l10n_co_edi.payment.option', string="Payment Option")

    @api.model
    def _load_pos_data_fields(self, config_id):
        # EXTENDS point_of_sale
        data_fields = super()._load_pos_data_fields(config_id)

        if self.env.company.l10n_co_edi_pos_dian_enabled:
            data_fields.append('l10n_co_edi_pos_payment_option_id')

        return data_fields
