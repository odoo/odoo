# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
import re
from lxml import etree
from psycopg2 import sql
from unittest.mock import Mock, MagicMock, patch

import werkzeug

import odoo
from odoo.tools.misc import DotDict


def get_video_embed_code(video_url):
    ''' Computes the valid iframe from given URL that can be embedded
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
        embedUrl = False
        ytMatch = re.search(ytRegex, video_url)
        vimeoMatch = re.search(vimeoRegex, video_url)
        dmMatch = re.search(dmRegex, video_url)
        igMatch = re.search(igRegex, video_url)
        ykuMatch = re.search(ykuRegex, video_url)

        if ytMatch and len(ytMatch.groups()[1]) == 11:
            embedUrl = '//www.youtube%s.com/embed/%s?rel=0' % (ytMatch.groups()[0] or '', ytMatch.groups()[1])
        elif vimeoMatch:
            embedUrl = '//player.vimeo.com/video/%s' % (vimeoMatch.groups()[2])
        elif dmMatch:
            embedUrl = '//www.dailymotion.com/embed/video/%s' % (dmMatch.groups()[1])
        elif igMatch:
            embedUrl = '//www.instagram.com/p/%s/embed/' % (igMatch.groups()[1])
        elif ykuMatch:
            ykuLink = ykuMatch.groups()[2]
            if '.html?' in ykuLink:
                ykuLink = ykuLink.split('.html?')[0]
            embedUrl = '//player.youku.com/embed/%s' % (ykuLink)
        else:
            # We directly use the provided URL as it is
            embedUrl = video_url
        return '<iframe class="embed-responsive-item" src="%s" allowFullScreen="true" frameborder="0"></iframe>' % embedUrl


def werkzeugRaiseNotFound(*args, **kwargs):
    raise werkzeug.exceptions.NotFound()


@contextlib.contextmanager
def MockRequest(
        env, *, routing=True, multilang=True,
        context=None,
        cookies=None, country_code=None, website=None, sale_order_id=None,
        website_sale_current_pl=None,
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
            path='/hello',
            app=odoo.http.root,
            environ={'REMOTE_ADDR': '127.0.0.1'},
            cookies=cookies or {},
            referrer='',
        ),
        lang=env['res.lang']._lang_get(lang_code),
        redirect=env['ir.http']._redirect,
        session=DotDict(
            geoip={'country_code': country_code},
            debug=False,
            sale_order_id=sale_order_id,
            website_sale_current_pl=website_sale_current_pl,
        ),
        website=website
    )

    with contextlib.ExitStack() as s:
        odoo.http._request_stack.push(request)
        s.callback(odoo.http._request_stack.pop)
        s.enter_context(patch('odoo.http.root.get_db_router', router))

        yield request

# Fuzzy matching tools

def distance(s1="", s2="", limit=4):
    """
    Limited Levenshtein-ish distance (inspired from Apache text common)
    Note: this does not return quick results for simple cases (empty string, equal strings)
        those checks should be done outside loops that use this function.

    :param s1: first string
    :param s2: second string
    :param limit: maximum distance to take into account, return -1 if exceeded

    :return: number of character changes needed to transform s1 into s2 or -1 if this exceeds the limit
    """
    BIG = 100000 # never reached integer
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    l1 = len(s1)
    l2 = len(s2)
    if l2 - l1 > limit:
        return -1
    boundary = min(l1, limit) + 1
    p = [i if i < boundary else BIG for i in range(0, l1 + 1)]
    d = [BIG for _ in range(0, l1 + 1)]
    for j in range(1, l2 + 1):
        j2 = s2[j -1]
        d[0] = j
        range_min = max(1, j - limit)
        range_max = min(l1, j + limit)
        if range_min > 1:
            d[range_min -1] = BIG
        for i in range(range_min, range_max + 1):
            if s1[i - 1] == j2:
                d[i] = p[i - 1]
            else:
                d[i] = 1 + min(d[i - 1], p[i], p[i - 1])
        p, d = d, p
    return p[l1] if p[l1] <= limit else -1

def similarity_score(s1, s2):
    """
    Computes a score that describes how much two strings are matching.

    :param s1: first string
    :param s2: second string

    :return: float score, the higher the more similar
        pairs returning non-positive scores should be considered non similar
    """
    dist = distance(s1, s2)
    if dist == -1:
        return -1
    set1 = set(s1)
    score = len(set1.intersection(s2)) / len(set1)
    score -= dist / len(s1)
    score -= len(set1.symmetric_difference(s2)) / (len(s1) + len(s2))
    return score

def text_from_html(html_fragment):
    """
    Returns the plain non-tag text from an html

    :param html_fragment: document from which text must be extracted

    :return: text extracted from the html
    """
    # lxml requires one single root element
    tree = etree.fromstring('<p>%s</p>' % html_fragment, etree.XMLParser(recover=True))
    return ' '.join(tree.itertext())

def get_unaccent_sql_wrapper(cr):
    """
    Returns a function that wraps SQL within unaccent if available
    TODO remove when this tool becomes globally available

    :param cr: cursor on which the wrapping is done

    :return: function that wraps SQL with unaccent if available
    """
    if odoo.registry(cr.dbname).has_unaccent:
        return lambda x: sql.SQL("unaccent({wrapped_sql})").format(wrapped_sql=x)
    return lambda x: x
