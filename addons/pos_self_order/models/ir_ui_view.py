# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    @api.model
    def _load_pos_self_data_read(self, records, config):
        read_records = super()._load_pos_self_data_read(records, config)

        for key in self._get_xml_ids_to_load():
            read_records.append({
                'key': key,
                '_template': self.env['ir.qweb']._get_template(key)[1],
            })

        return read_records
