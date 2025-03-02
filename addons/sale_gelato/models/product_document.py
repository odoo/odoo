# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductDocument(models.Model):

    _inherit = 'product.document'

    # Technical field to tell apart Gelato print images from other product documents.
    is_gelato = fields.Boolean(readonly=True)

    def _gelato_prepare_file_payload(self):
        """ Create the payload for a single file of an 'orders' request.

        :return: The file payload.
        :rtype: dict
        """
        if not self.datas:
            raise UserError(_("Print images must be set on products before they can be ordered."))

        query_string = f'access_token={self.ir_attachment_id.generate_access_token()[0]}'
        url = f'{self.get_base_url()}{self.ir_attachment_id.image_src}?{query_string}'
        return {
            'type': self.name.lower(),  # Gelato requires lowercase types.
            'url': url,
        }
