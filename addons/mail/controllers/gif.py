from odoo import http
from odoo.http import request


class GifController(http.Controller):

    @http.route('/mail/set_gif_favorite', type='json', auth='user')
    def set_gif_favorite(self, gif_id):
        request.env['mail.gif_favorite'].create({
            'gif_id': gif_id
        })

    @http.route('/mail/get_gif_favorites', type='json', auth='user')
    def get_gif_favorites(self, offset=0):
        return {
            'results': request.env['mail.gif_favorite'].search_read([('create_uid', '=', request.env.user.id)], limit=20, offset=offset) or False,
            'offset': offset + 20
        }

    @http.route('/mail/remove_gif_favorites', type='json', auth='user')
    def remove_gif_favorites(self, gif_id):
        return request.env['mail.gif_favorite'].search([('gif_id', '=', gif_id)]).unlink()
