# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re
import requests

from markupsafe import Markup
from werkzeug.urls import url_encode

from odoo import _
from odoo.tools import image_process

# To detect if we have a valid URL or not
valid_url_regex = r'^(http://|https://|//)[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(/.*)?$'

# Regex for few of the widely used video hosting services
player_regexes = {
    'youtube': r'^(?:(?:https?:)?//)?(?:www\.)?(?:youtu\.be/|youtube(-nocookie)?\.com/(?:embed/|v/|watch\?v=|watch\?.+&v=))((?:\w|-){11})\S*$',
    'vimeo': r'//(player.)?vimeo.com/([a-z]*/)*([0-9]{6,11})[?]?.*',
    'dailymotion': r'(?:.+dailymotion.com/(video|hub|embed/video|embed)|dai\.ly)/([^_?]+)[^#]*(#video=([^_&]+))?',
    'instagram': r'(?:(.*)instagram.com|instagr\.am)/p/(.[a-zA-Z0-9-_\.]*)',
    'youku': r'(.*).youku\.com/(v_show/id_|embed/)(.+)',
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
            return ('dailymotion', dailymotion_match[2], dailymotion_match)
        instagram_match = re.search(player_regexes['instagram'], video_url)
        if instagram_match:
            return ('instagram', instagram_match[2], instagram_match)
        youku_match = re.search(player_regexes['youku'], video_url)
        if youku_match:
            youku_link = youku_match[3]
            if '.html?' in youku_link:
                youku_link = youku_link.split('.html?')[0]
            return ('youku', youku_link, youku_match)
    return None


def get_video_url_data(video_url, autoplay=False, loop=False, hide_controls=False, hide_fullscreen=False, hide_yt_logo=False, hide_dm_logo=False, hide_dm_share=False):
    """ Computes the platform name and embed_url from given URL
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
        if hide_yt_logo:
            params['modestbranding'] = 1
        yt_extra = platform_match[1] or ''
        embed_url = f'//www.youtube{yt_extra}.com/embed/{video_id}'
    elif platform == 'vimeo':
        params['autoplay'] = autoplay and 1 or 0
        if autoplay:
            params['muted'] = 1
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

    return {'platform': platform, 'embed_url': embed_url}


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
