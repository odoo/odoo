# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_es_pos_refund_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string="Simplified Credit Note Sequence",
        help="Numbers the simplified credit notes of this point of sale, in their own series.",
        readonly=True,
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        # EXTENDS 'point_of_sale'
        configs = super().create(vals_list)
        configs._l10n_es_pos_create_refund_sequence()
        return configs

    def _l10n_es_pos_create_refund_sequence(self):
        """Create the sequence of the simplified credit notes of the points of sale missing one.

        It is created with the point of sale (and for the existing ones when installing the module),
        never when the first refund is paid: two devices paying their first refund at the same time
        would create a sequence each and issue the same number twice.
        """
        for config in self.filtered(lambda config: not config.l10n_es_pos_refund_sequence_id):
            config.l10n_es_pos_refund_sequence_id = self.env['ir.sequence'].sudo().create({
                'name': _("Simplified credit notes of %s", config.name),
                'implementation': 'no_gap',
                'padding': 6,
                'company_id': config.company_id.id,
            })

    def _load_pos_data_read(self, records, config):
        # EXTENDS 'point_of_sale'
        read_records = super()._load_pos_data_read(records, config)
        if read_records:
            fiscal_mode = config.company_id._l10n_es_pos_get_fiscal_mode()
            read_records[0]['_l10n_es_pos_fiscal_mode'] = fiscal_mode
            if fiscal_mode:
                read_records[0]['_l10n_es_refund_reasons'] = self.env['pos.order']._l10n_es_pos_get_refund_reasons()
        return read_records
