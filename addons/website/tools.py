# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import contextlib
import json
import re
from unittest.mock import Mock, MagicMock, patch

import werkzeug
import requests

import odoo
from odoo.tools.misc import DotDict
from odoo.tools import image_process
from odoo.modules.module import get_module_resource


def get_video_platform_and_id(video_url):
    ''' Computes the valid source and document ID from given URL
        (or False in case of invalid URL).
    '''
    if not video_url:
        return False

    # To detect if we have a valid URL or not
    validURLRegex = r'^(http:\/\/|https:\/\/|\/\/)[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?$'

    # Regex for few of the widely used video hosting services
    ytRegex = r'^(?:(?:https?:)?\/\/)?(?:www\.)?(?:youtu\.be\/|youtube(-nocookie)?\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((?:\w|-){11})(?:\S+)?$'
    vimeoRegex = r'\/\/(player.)?vimeo.com\/([a-z]*\/)*([0-9]{6,11})[?]?.*'
    dmRegex = r'.+dailymotion.com\/(video|hub|embed)\/([^_?]+)[^#]*(#video=([^_&]+))?'
    igRegex = r'(.*)instagram.com\/p\/(.[a-zA-Z0-9]*)'
    ykuRegex = r'(.*).youku\.com\/(v_show\/id_|embed\/)(.+)'

    if not re.search(validURLRegex, video_url):
        return False
    else:
        ytMatch = re.search(ytRegex, video_url)
        vimeoMatch = re.search(vimeoRegex, video_url)
        dmMatch = re.search(dmRegex, video_url)
        igMatch = re.search(igRegex, video_url)
        ykuMatch = re.search(ykuRegex, video_url)

        if ytMatch and len(ytMatch.groups()[1]) == 11:
            return ('youtube', ytMatch.groups()[1], ytMatch)
        elif vimeoMatch:
            return ('vimeo', vimeoMatch.groups()[2], vimeoMatch)
        elif dmMatch:
            justId = dmMatch.groups()[1].replace('video/', '')
            return ('dailymotion', justId, dmMatch)
        elif igMatch:
            return ('instagram', igMatch.groups()[1], igMatch)
        elif ykuMatch:
            ykuLink = ykuMatch.groups()[2]
            if '.html?' in ykuLink:
                ykuLink = ykuLink.split('.html?')[0]
            return ('youku', ykuLink, ykuMatch)
        else:
            return video_url

def get_video_embed_code(video_url):
    ''' Computes the valid iframe from given URL that can be embedded
        (or False in case of invalid URL).
    '''
    source = get_video_platform_and_id(video_url)
    if not source:
        return False

    # We directly use the provided URL as it is
    embedUrl = video_url
    if isinstance(source, tuple):
        platform = source[0]
        platform_id = source[1]
        platform_match = source[2]
        if platform == 'youtube' and len(platform_id) == 11:
            embedUrl = '//www.youtube%s.com/embed/%s?rel=0' % (platform_match.groups()[0] or '', platform_id)
        elif platform == 'vimeo':
            embedUrl = '//player.vimeo.com/video/%s' % (platform_id)
        elif platform == 'dailymotion':
            justId = platform_id.replace('video/', '')
            embedUrl = '//www.dailymotion.com/embed/video/%s' % (justId)
        elif platform == 'instagram':
            embedUrl = '//www.instagram.com/p/%s/embed/' % (platform_id)
        elif platform == 'youku':
            embedUrl = '//player.youku.com/embed/%s' % (platform_id)

    return '<iframe class="embed-responsive-item" src="%s" allowFullScreen="true" frameborder="0"></iframe>' % embedUrl

def get_video_thumbnail(video_url):
    ''' Computes the valid thumbnail image from given URL
        (or False in case of invalid URL).
    '''
    source = get_video_platform_and_id(video_url)
    if not source:
        return False

    response = False
    if isinstance(source, tuple):
        platform = source[0]
        platform_id = source[1]
        if platform == 'youtube' and len(platform_id) == 11:
            response = requests.get('https://img.youtube.com/vi/'+ platform_id + '/0.jpg')
        elif platform == 'vimeo':
            vimeo_req = requests.get('https://vimeo.com/api/oembed.json?url='+ video_url)
            if vimeo_req.status_code == 200:
                data = json.loads(vimeo_req.content)
                response = requests.get(data['thumbnail_url'])
        elif platform == 'dailymotion':
            response = requests.get('https://www.dailymotion.com/thumbnail/video/'+ platform_id)
        elif platform == 'instagram':
            response = requests.get('https://www.instagram.com/p/'+ platform_id + '/media/?size=t')

    if response and response.status_code == 200:
        return image_process(base64.b64encode(response.content))
    else:
        #set a default image
        image_path = get_module_resource('web', 'static/src/img', 'placeholder.png')
        return image_process(base64.b64encode(open(image_path, 'rb').read()))


def werkzeugRaiseNotFound(*args, **kwargs):
    raise werkzeug.exceptions.NotFound()


@contextlib.contextmanager
def MockRequest(
        env, *, routing=True, multilang=True,
        context=None,
        cookies=None, country_code=None, website=None, sale_order_id=None
):
    router = MagicMock()
    match = router.return_value.bind.return_value.match
    if routing:
        match.return_value[0].routing = {
            'type': 'http',
            'website': True,
            'multilang': multilang
        }
    else:
        match.side_effect = werkzeugRaiseNotFound

    if context is None:
        context = {}
    lang_code = context.get('lang', env.context.get('lang', 'en_US'))
    context.setdefault('lang', lang_code)

    request = Mock(
        context=context,
        db=None,
        endpoint=match.return_value[0] if routing else None,
        env=env,
        httprequest=Mock(
            host='localhost',
            path='/hello/',
            app=odoo.http.root,
            environ={'REMOTE_ADDR': '127.0.0.1'},
            cookies=cookies or {},
            referrer='',
        ),
        lang=env['res.lang']._lang_get(lang_code),
        redirect=werkzeug.utils.redirect,
        session=DotDict(
            geoip={'country_code': country_code},
            debug=False,
            sale_order_id=sale_order_id,
        ),
        website=website
    )

    with contextlib.ExitStack() as s:
        odoo.http._request_stack.push(request)
        s.callback(odoo.http._request_stack.pop)
        s.enter_context(patch('odoo.http.root.get_db_router', router))

        yield request
