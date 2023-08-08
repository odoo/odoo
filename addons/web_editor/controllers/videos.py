from odoo import http


class Video(http.Controller):
    @http.route('/web/content/thumbnail/<int:id>', type='http', auth='public', website=True)
    def thumbnail(self, id, **kwargs):
        attachment = http.request.env['ir.attachment'].sudo().browse(id)
        if not attachment or not attachment.thumbnail:
            return http.request.redirect('/web/image/web_editor.s_video_placeholder')

        return http.request.redirect(f"/web/image/{attachment.thumbnail.id}")

    @http.route('/watch/<int:id>', type='http', auth='public', website=True)
    def watch(self, id=None, autoplay='0', mute='0', loop='0', controls='1', **kwargs):
        # Convert parms to boolean
        videoAttr = {}
        if autoplay == '1':
            videoAttr['autoplay'] = 1
        if mute == '1':
            videoAttr['muted'] = 1
        videoAttr['loop'] = loop == '1'
        if controls == '1':
            videoAttr['controls'] = "nodownload"

        sourceAttr = {}
        sourceAttr['src'] = f"/web/content/{id}"
        sourceAttr['type'] = "video/mp4"

        return http.request.render('web_editor.player', {
            'videoAttr': videoAttr,
            'sourceAttr': sourceAttr,
        })

