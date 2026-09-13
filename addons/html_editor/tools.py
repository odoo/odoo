import contextlib
import logging
import re
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from markupsafe import Markup

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.libs import guarded_http, netguard
from odoo.tools.image import image_process

_logger = logging.getLogger(__name__)

valid_url_regex = r"^(http://|https://|//)[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(/.*)?$"

player_regexes = {
    "youtube": r"^(?:(?:https?:)?//)?(?:www\.|m\.)?(?:youtu\.be/|youtube(-nocookie)?\.com/(?:embed/|v/|shorts/|live/|watch\?v=|watch\?.+&v=))((?:\w|-){11})\S*$",
    "vimeo": r"//(player.)?vimeo.com/([a-z]*/)?(?P<id>[^/\?]+)(?:/(?P<hash>[^/\?]+))?(?:\?(?P<params>[^\s]+))?$",
    "dailymotion": r"(https?:\/\/)(www\.)?(dailymotion\.com\/(embed\/video\/|embed\/|video\/|hub\/.*#video=)|geo\.dailymotion\.com\/player\.html\?video=|dai\.ly\/)(?P<id>[A-Za-z0-9]{6,7})",
    "instagram": r"(?:(.*)instagram.com|instagr\.am)/p/(.[a-zA-Z0-9-_\.]*)",
    "facebook": r"^(?:(?:https?:)?//)?(?:www\.)?facebook\.com(?:/(?:[^/]+/)?videos/|/watch/?\?v=|/reel/|/plugins/video\.php\?[^ ]*?href=.*?(?:videos|reel)%2[Ff])(?P<id>\d+)",
}

VIDEO_THUMBNAIL_MAX_BYTES = 10 * 1024 * 1024


def get_video_source_data(video_url):
    if not video_url:
        return None

    if re.search(valid_url_regex, video_url):
        youtube_match = re.search(player_regexes["youtube"], video_url)
        if youtube_match:
            return ("youtube", youtube_match[2], youtube_match)
        vimeo_match = re.search(player_regexes["vimeo"], video_url)
        if vimeo_match:
            return ("vimeo", vimeo_match.group("id"), vimeo_match)
        dailymotion_match = re.search(player_regexes["dailymotion"], video_url)
        if dailymotion_match:
            return ("dailymotion", dailymotion_match.group("id"), dailymotion_match)
        instagram_match = re.search(player_regexes["instagram"], video_url)
        if instagram_match:
            return ("instagram", instagram_match[2], instagram_match)
        facebook_match = re.search(player_regexes["facebook"], video_url)
        if facebook_match:
            return ("facebook", facebook_match.group("id"), facebook_match)
    return None


def _youtube_embed_url(
    video_id,
    platform_match,
    params,
    *,
    autoplay,
    loop,
    hide_controls,
    hide_fullscreen,
    start_from,
):
    params["rel"] = 0
    params["autoplay"] = (autoplay and 1) or 0
    if start_from:
        params["start"] = start_from.rstrip("s")
    if autoplay:
        params["mute"] = 1
        params["enablejsapi"] = 1
    if hide_controls:
        params["controls"] = 0
    if loop:
        params["loop"] = 1
        params["playlist"] = video_id
    if hide_fullscreen:
        params["fs"] = 0
    yt_extra = platform_match[1] or ""
    return f"//www.youtube{yt_extra}.com/embed/{video_id}?{urlencode(params)}"


def _vimeo_embed_url(
    video_id, platform_match, params, *, autoplay, loop, hide_controls, start_from
):
    params["autoplay"] = (autoplay and 1) or 0
    params["dnt"] = 1
    if autoplay:
        params["muted"] = 1
        params["autopause"] = 0
    if hide_controls:
        params["controls"] = 0
    if loop:
        params["loop"] = 1
    groups = platform_match.groupdict()
    if groups.get("hash"):
        params["h"] = groups["hash"]
    elif groups.get("params"):
        url_params = parse_qs(groups["params"])
        if "h" in url_params:
            params["h"] = url_params["h"][0]
    embed_url = f"//player.vimeo.com/video/{video_id}?{urlencode(params)}"
    if start_from:
        embed_url = f"{embed_url}#t={start_from}"
    return embed_url


def get_video_url_data(
    video_url,
    autoplay=False,
    loop=False,
    hide_controls=False,
    hide_fullscreen=False,
    hide_dm_logo=False,
    hide_dm_share=False,
    start_from=False,
):
    source = get_video_source_data(video_url)
    if source is None:
        return {"error": True, "message": _("The provided url is invalid")}

    embed_url = video_url
    platform, video_id, platform_match = source

    params = {}
    if start_from == "00:00":
        start_from = "0"
    if platform == "youtube":
        embed_url = _youtube_embed_url(
            video_id,
            platform_match,
            params,
            autoplay=autoplay,
            loop=loop,
            hide_controls=hide_controls,
            hide_fullscreen=hide_fullscreen,
            start_from=start_from,
        )
    elif platform == "vimeo":
        embed_url = _vimeo_embed_url(
            video_id,
            platform_match,
            params,
            autoplay=autoplay,
            loop=loop,
            hide_controls=hide_controls,
            start_from=start_from,
        )
    elif platform == "dailymotion":
        if start_from:
            params["startTime"] = start_from.rstrip("s")
        embed_url = (
            f"//geo.dailymotion.com/player.html?video={video_id}&{urlencode(params)}"
        )
    elif platform == "instagram":
        embed_url = f"//www.instagram.com/p/{video_id}/embed/"
    elif platform == "facebook":
        embed_url = f"//facebook.com/plugins/video.php?href=https://www.facebook.com/username/videos/{video_id}/"

    return {
        "platform": platform,
        "embed_url": embed_url,
        "video_id": video_id,
        "params": params,
    }


def get_video_embed_code(video_url):
    parsed_url = urlparse(video_url)
    query_params = parse_qs(parsed_url.query)
    param_name_mapping = {
        "autoplay": "autoplay",
        "loop": "loop",
        "hide_controls": "controls",
        "hide_fullscreen": "fs",
        "hide_dm_logo": "ui-logo",
        "hide_dm_share": "sharing-enable",
    }
    params = {
        func_param: int(query_params[url_param][0]) if func_param == "autoplay" else 1
        for func_param, url_param in param_name_mapping.items()
        if url_param in query_params
    }
    data = get_video_url_data(video_url, **params)
    if "error" in data:
        return None
    return (
        Markup(
            '<iframe class="embed-responsive-item" src="%s" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowFullScreen="true" frameborder="0"></iframe>'
        )
        % data["embed_url"]
    )


def get_video_thumbnail(video_url):
    source = get_video_source_data(video_url)
    if source is None:
        return None

    response = None
    platform, video_id = source[:2]
    session = guarded_http.guarded_session(
        netguard.PUBLIC_ONLY, max_bytes=VIDEO_THUMBNAIL_MAX_BYTES
    )
    with session, contextlib.suppress(requests.exceptions.RequestException):
        if platform == "youtube":
            response = session.get(
                f"https://img.youtube.com/vi/{video_id}/0.jpg", timeout=10
            )
        elif platform == "vimeo":
            res = session.get(
                "https://vimeo.com/api/oembed.json",
                params={"url": video_url},
                timeout=10,
            )
            if res.ok:
                data = res.json()
                response = session.get(data["thumbnail_url"], timeout=10)
        elif platform == "dailymotion":
            response = session.get(
                f"https://www.dailymotion.com/thumbnail/video/{video_id}", timeout=10
            )
        elif platform == "instagram":
            response = session.get(
                f"https://www.instagram.com/p/{video_id}/media/?size=t", timeout=10
            )

    if response and response.ok:
        return image_process(response.content)
    return None


diverging_history_regex = 'data-last-history-steps="([0-9,]+)"'


def handle_history_divergence(record, html_field_name, vals):
    if html_field_name not in vals:
        return
    if record.env.context.get("install_module"):
        return
    incoming_html = vals[html_field_name]
    incoming_history_matches = re.search(diverging_history_regex, incoming_html or "")

    def _notify_bus(last_step_id):
        if not request:
            return
        channel = (
            request.db,
            "editor_collaboration",
            record._name,
            html_field_name,
            record.id,
        )
        bus_data = {
            "model_name": record._name,
            "field_name": html_field_name,
            "res_id": record.id,
            "notificationName": "html_field_write",
            "notificationPayload": {"last_step_id": last_step_id},
        }
        request.env["bus.bus"]._sendone(channel, "editor_collaboration", bus_data)

    if incoming_history_matches is None:
        _notify_bus(None)
        return
    incoming_history_ids = incoming_history_matches[1].split(",")
    last_step_id = incoming_history_ids[-1]

    _notify_bus(last_step_id)

    if record[html_field_name]:
        server_history_matches = re.search(
            diverging_history_regex, record[html_field_name] or ""
        )
        if server_history_matches:
            server_last_history_id = server_history_matches[1].split(",")[-1]
            if server_last_history_id not in incoming_history_ids:
                _logger.warning(
                    "The document was already saved from someone with a different history for model %r, field %r with id %r.",
                    record._name,
                    html_field_name,
                    record.id,
                )
                raise ValidationError(
                    _(
                        'The document was already saved from someone with a different history for model "%(model)s", field "%(field)s" with id "%(id)d".',
                        model=record._name,
                        field=html_field_name,
                        id=record.id,
                    )
                )

    vals[html_field_name] = (
        incoming_html[0 : incoming_history_matches.start(1)]
        + last_step_id
        + incoming_html[incoming_history_matches.end(1) :]
    )
