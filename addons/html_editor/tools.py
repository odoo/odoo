# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from werkzeug.urls import url_encode

from odoo import _

logger = logging.getLogger(__name__)

# To detect if we have a valid URL or not
valid_url_regex = r'^(http://|https://|//)[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(/.*)?$'

# Regex for few of the widely used video hosting services
player_regexes = {
    'youtube': r'^(?:(?:https?:)?//)?(?:www\.)?(?:youtu\.be/|youtube(-nocookie)?\.com/(?:embed/|v/|shorts/|live/|watch\?v=|watch\?.+&v=))((?:\w|-){11})\S*$',
    'vimeo': r'//(player.)?vimeo.com/([a-z]*/)*([0-9]{6,11})[?]?.*',
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
        vimeo_match = re.search(player_regexes['vimeo'], video_url)
        if vimeo_match:
            return ('vimeo', vimeo_match[3], vimeo_match)
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


def get_video_url_data(video_url, autoplay=False, loop=False, hide_controls=False, hide_fullscreen=False, hide_dm_logo=False, hide_dm_share=False):
    """ Computes the platform name, the embed_url, the video id and the video params of the given URL
        (or error message in case of invalid URL).
    """
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
