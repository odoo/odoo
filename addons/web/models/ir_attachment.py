# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def web_create_image_variants(self, variants):
        """Create linked image variants in batch using `create_unique`."""
        ids = []
        main_attachment_id = False

        for variant in variants:
            values_list = variant.get('images', [])
            if not values_list:
                continue

            resized_attachment_id = False

            for vals in values_list:
                values = dict(vals)
                values['res_model'] = 'ir.attachment'
                values['res_id'] = resized_attachment_id or main_attachment_id

                created_ids = self.create_unique([values])
                attachment_id = created_ids[0].id if created_ids else False
                ids.append(attachment_id)

                resized_attachment_id = attachment_id
                main_attachment_id = main_attachment_id or attachment_id

        return ids
