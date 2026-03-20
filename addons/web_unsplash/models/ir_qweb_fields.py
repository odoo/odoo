from werkzeug import urls

from odoo import models, api


class IrQwebFieldImage(models.AbstractModel):
    _inherit = 'ir.qweb.field.image'

    @api.model
    def from_html(self, model, field, element):
        if element.find('.//img') is None:
            return False
        url = element.find('.//img').get('src')
        url_object = urls.url_parse(url)

        if url_object.path.startswith('/unsplash/'):
            res_id = element.get('data-oe-id')
            if res_id:
                res_id = int(res_id)
                res_model = model._name
                attachment = self.env['ir.attachment'].search([
                    '&', '|', '&',
                    ('res_model', '=', res_model),
                    ('res_id', '=', res_id),
                    ('public', '=', True),
                    ('url', '=', url_object.path),
                ], limit=1)
                return attachment.datas

        return super().from_html(model, field, element)
