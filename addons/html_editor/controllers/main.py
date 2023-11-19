

from odoo import http
from odoo.addons.html_editor.tools import get_video_url_data

class HTML_Editor(http.Controller):
    @http.route('/html_editor/video_url/data', type='json', auth='user', website=True)
    def video_url_data(self, video_url, autoplay=False, loop=False,
                       hide_controls=False, hide_fullscreen=False, hide_yt_logo=False,
                       hide_dm_logo=False, hide_dm_share=False):
        return get_video_url_data(
            video_url, autoplay=autoplay, loop=loop,
            hide_controls=hide_controls, hide_fullscreen=hide_fullscreen,
            hide_yt_logo=hide_yt_logo, hide_dm_logo=hide_dm_logo,
            hide_dm_share=hide_dm_share
        )
