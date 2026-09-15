from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.website_slides.controllers.main import WebsiteSlides

_debug = DebugLog(__name__)


class WebsiteSlidesForum(WebsiteSlides):
    def _prepare_user_profile_parameters(self, **post):
        post = super()._prepare_user_profile_parameters(**post)
        if post.get("channel_id"):
            channel = request.env["slide.channel"].browse(int(post.get("channel_id")))
            _debug.logic("profile_forum_scope", channel=channel, forum=channel.forum_id)
            if channel.forum_id:
                post.update({"forum_id": channel.forum_id.id, "no_forum": False})
            else:
                post.update({"no_forum": True})
        return post
