# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class LoyaltyReward(models.Model):
    _name = 'loyalty.reward'
    _inherit = ['loyalty.reward']

    image_512 = fields.Image("Image", max_width=512, max_height=512)
    image_128 = fields.Image("Image 128", related="image_512", max_width=128, max_height=128)

    @api.model
    def _load_pos_self_data_read(self, records, config):
        read_records = super()._load_pos_self_data_read(records, config)
        for read_record in read_records:
            record = self.browse(read_record['id'])
            read_record['_has_image'] = bool(record.image_128)
        return read_records

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name in ["image_512", "image_128"] and self.sudo().program_id.pos_ok:
            configs = self.sudo().program_id.pos_config_ids or self.sudo().env['pos.config'].search([*self._check_company_domain(self.sudo().company_id.id)])
            if any(config.self_ordering_mode in ['mobile', 'kiosk'] for config in configs):
                return True
        return super()._can_return_content(field_name, access_token)
