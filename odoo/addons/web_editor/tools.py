# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import contextlib
import logging
import re
import requests

from markupsafe import Markup
from urllib.parse import parse_qs
from werkzeug.urls import url_encode

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import image_process

logger = logging.getLogger(__name__)

# To detect if we have a valid URL or not
valid_url_regex = r'^(http://|https://|//)[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(/.*)?$'

# Regex for few of the widely used video hosting services
player_regexes = {
    'youtube': r'^(?:(?:https?:)?//)?(?:www\.|m\.)?(?:youtu\.be/|youtube(-nocookie)?\.com/(?:embed/|v/|shorts/|live/|watch\?v=|watch\?.+&v=))((?:\w|-){11})\S*$',
    'vimeo': r'^(?:(?:https?:)?//)?(?:www\.)?vimeo\.com\/(?P<id>[^/\?]+)(?:/(?P<hash>[^/\?]+))?(?:\?(?P<params>[^\s]+))?$',
    'vimeo_player': r'^(?:(?:https?:)?//)?player\.vimeo\.com\/video\/(?P<id>[^/\?]+)(?:\?(?P<params>[^\s]+))?$',
    'dailymotion': r'(https?:\/\/)(www\.)?(dailymotion\.com\/(embed\/video\/|embed\/|video\/|hub\/.*#video=)|dai\.ly\/)(?P<id>[A-Za-z0-9]{6,7})',
    'instagram': r'(?:(.*)instagram.com|instagr\.am)/p/(.[a-zA-Z0-9-_\.]*)',
    'youku': r'(?:(https?:\/\/)?(v\.youku\.com/v_show/id_|player\.youku\.com/player\.php/sid/|player\.youku\.com/embed/|cloud\.youku\.com/services/sharev\?vid=|video\.tudou\.com/v/)|youku:)(?P<id>[A-Za-z0-9]+)(?:\.html|/v\.swf|)',
}


def get_video_source_data(video_url):
    """ Computes the valid source, document ID and regex match from given URL
        (or None in case of invalid URL).
    """
    if not video_url:
        return None

    if re.search(valid_url_regex, video_url):
        youtube_match = re.search(player_regexes['youtube'], video_url)
        if youtube_match:
            return ('youtube', youtube_match[2], youtube_match)
        vimeo_match = (
            re.search(player_regexes['vimeo'], video_url) or
            re.search(player_regexes['vimeo_player'], video_url))
        if vimeo_match:
            return ('vimeo', vimeo_match.group('id'), vimeo_match)
        dailymotion_match = re.search(player_regexes['dailymotion'], video_url)
        if dailymotion_match:
            return ('dailymotion', dailymotion_match.group("id"), dailymotion_match)
        instagram_match = re.search(player_regexes['instagram'], video_url)
        if instagram_match:
            return ('instagram', instagram_match[2], instagram_match)
        youku_match = re.search(player_regexes['youku'], video_url)
        if youku_match:
            return ('youku', youku_match.group("id"), youku_match)
    return None


def get_video_url_data(video_url, autoplay=False, loop=False, hide_controls=False, hide_fullscreen=False, hide_yt_logo=False, hide_dm_logo=False, hide_dm_share=False):
    """ Computes the platform name, the embed_url, the video id and the video params of the given URL
        (or error message in case of invalid URL).
    """
    # TODO: In Master, remove the parameter "hide_yt_logo" (the parameter is no
    # longer supported in the YouTube API.)
    source = get_video_source_data(video_url)
    if source is None:
        return {'error': True, 'message': _('The provided url is invalid')}

    embed_url = video_url
    platform, video_id, platform_match = source

    params = {}

    if platform == 'youtube':
        params['rel'] = 0
        params['autoplay'] = autoplay and 1 or 0
        if autoplay:
            params['mute'] = 1
            # The youtube js api is needed for autoplay on mobile. Note: this
            # was added as a fix, old customers may have autoplay videos
            # without this, which will make their video autoplay on desktop but
            # not in mobile (so no behavior change was done in stable, this
            # should not be migrated).
            params['enablejsapi'] = 1
        if hide_controls:
            params['controls'] = 0
        if loop:
            params['loop'] = 1
            params['playlist'] = video_id
        if hide_fullscreen:
            params['fs'] = 0
        yt_extra = platform_match[1] or ''
        embed_url = f'//www.youtube{yt_extra}.com/embed/{video_id}'
    elif platform == 'vimeo':
        params['autoplay'] = autoplay and 1 or 0
        if autoplay:
            params['muted'] = 1
            params['autopause'] = 0
        if hide_controls:
            params['controls'] = 0
        if loop:
            params['loop'] = 1
        groups = platform_match.groupdict()
        if groups.get('hash'):
            params['h'] = groups['hash']
        elif groups.get('params'):
            url_params = parse_qs(groups['params'])
            if 'h' in url_params:
                params['h'] = url_params['h'][0]
        embed_url = f'//player.vimeo.com/video/{video_id}'
    elif platform == 'dailymotion':
        params['autoplay'] = autoplay and 1 or 0
        if autoplay:
            params['mute'] = 1
        if hide_controls:
            params['controls'] = 0
        if hide_dm_logo:
            params['ui-logo'] = 0
        if hide_dm_share:
            params['sharing-enable'] = 0
        embed_url = f'//www.dailymotion.com/embed/video/{video_id}'
    elif platform == 'instagram':
        embed_url = f'//www.instagram.com/p/{video_id}/embed/'
    elif platform == 'youku':
        embed_url = f'//player.youku.com/embed/{video_id}'

    if params:
        embed_url = f'{embed_url}?{url_encode(params)}'

    return {
        'platform': platform,
        'embed_url': embed_url,
        'video_id': video_id,
        'params': params
    }


def get_video_embed_code(video_url):
    """ Computes the valid iframe from given URL that can be embedded
        (or None in case of invalid URL).
    """
    data = get_video_url_data(video_url)
    if 'error' in data:
        return None
    return Markup('<iframe class="embed-responsive-item" src="%s" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowFullScreen="true" frameborder="0"></iframe>') % data['embed_url']


def get_video_thumbnail(video_url):
    """ Computes the valid thumbnail image from given URL
        (or None in case of invalid URL).
    """
    source = get_video_source_data(video_url)
    if source is None:
        return None

    response = None
    platform, video_id = source[:2]
    with contextlib.suppress(requests.exceptions.RequestException):
        if platform == 'youtube':
            response = requests.get(f'https://img.youtube.com/vi/{video_id}/0.jpg', timeout=10)
        elif platform == 'vimeo':
            res = requests.get(f'http://vimeo.com/api/oembed.json?url={video_url}', timeout=10)
            if res.ok:
                data = res.json()
                response = requests.get(data['thumbnail_url'], timeout=10)
        elif platform == 'dailymotion':
            response = requests.get(f'https://www.dailymotion.com/thumbnail/video/{video_id}', timeout=10)
        elif platform == 'instagram':
            response = requests.get(f'https://www.instagram.com/p/{video_id}/media/?size=t', timeout=10)

    if response and response.ok:
        return image_process(response.content)
    return None

diverging_history_regex = 'data-last-history-steps="([0-9,]+)"'
# This method must be called in a context that has write access to the record as
# it will write to the bus.
def handle_history_divergence(record, html_field_name, vals):
    # Do not handle history divergence if the field is not in the values.
    if html_field_name not in vals:
        return
    # Do not handle history divergence if in module installation mode.
    if record.env.context.get('install_module'):
        return
    incoming_html = vals[html_field_name]
    incoming_history_matches = re.search(diverging_history_regex, incoming_html or '')
    # When there is no incoming history id, it means that the value does not
    # comes from the odoo editor or the collaboration was not activated. In
    # project, it could come from the collaboration pad. In that case, we do not
    # handle history divergences.
    if request:
        channel = (request.db, 'editor_collaboration', record._name, html_field_name, record.id)
    if incoming_history_matches is None:
        if request:
            bus_data = {
                'model_name': record._name,
                'field_name': html_field_name,
                'res_id': record.id,
                'notificationName': 'html_field_write',
                'notificationPayload': {'last_step_id': None},
            }
            request.env['bus.bus']._sendone(channel, 'editor_collaboration', bus_data)
        return
    incoming_history_ids = incoming_history_matches[1].split(',')
    last_step_id = incoming_history_ids[-1]

    bus_data = {
        'model_name': record._name,
        'field_name': html_field_name,
        'res_id': record.id,
        'notificationName': 'html_field_write',
        'notificationPayload': {'last_step_id': last_step_id},
    }
    if request:
        request.env['bus.bus']._sendone(channel, 'editor_collaboration', bus_data)

    if record[html_field_name]:
        server_history_matches = re.search(diverging_history_regex, record[html_field_name] or '')
        # Do not check old documents without data-last-history-steps.
        if server_history_matches:
            server_last_history_id = server_history_matches[1].split(',')[-1]
            if server_last_history_id not in incoming_history_ids:
                logger.warning('The document was already saved from someone with a different history for model %r, field %r with id %r.', record._name, html_field_name, record.id)
                raise ValidationError(_('The document was already saved from someone with a different history for model %r, field %r with id %r.', record._name, html_field_name, record.id))

    # Save only the latest id.
    vals[html_field_name] = incoming_html[0:incoming_history_matches.start(1)] + last_step_id + incoming_html[incoming_history_matches.end(1):]
