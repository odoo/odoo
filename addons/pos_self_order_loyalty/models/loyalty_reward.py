# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class LoyaltyReward(models.Model):
    _name = 'loyalty.reward'
    _inherit = ['loyalty.reward']

    image_512 = fields.Image("Image", max_width=512, max_height=512)
    image_128 = fields.Image("Image 128", related="image_512", max_width=128, max_height=128)

    @api.model
    def _load_pos_self_data_fields(self, config):
        fields = super()._load_pos_self_data_fields(config)
        fields += ['write_date']
        return fields

    @api.model
    def _load_pos_self_data_read(self, records, config):
        read_records = super()._load_pos_self_data_read(records, config)
        rewards = self.browse([r['id'] for r in read_records]).with_context(bin_size=True)
        for read_record, reward in zip(read_records, rewards):
            read_record['_has_image'] = bool(reward.image_512)
        return read_records

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name in ["image_512", "image_128"] and self.sudo().program_id.pos_ok:
            configs = self.sudo().program_id.pos_config_ids or self.sudo().env['pos.config'].search([*self._check_company_domain(self.sudo().company_id.id)])
            if any(config.self_ordering_mode in ['mobile', 'kiosk'] for config in configs):
                return True
        return super()._can_return_content(field_name, access_token)
