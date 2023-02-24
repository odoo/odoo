# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html
import requests


def get_link_preview_from_url(url, request_session=None):
    """
    Get the Open Graph properties of an url. (https://ogp.me/)
    If the url leads directly to an image mimetype, return
    the url as preview image else retrieve the properties from
    the html page.

    Using a stream request to prevent loading the whole page
    as those properties are declared in the <head> tag.

    The request session is optional as in some cases using
    a session could be beneficial performance wise
    (e.g. a lot of url could have the same domain).
    """
    # Some websites are blocking non browser user agent.
    user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'}
    try:
        if request_session:
            response = request_session.get(url, timeout=3, headers=user_agent, allow_redirects=True, stream=True)
        else:
            response = requests.get(url, timeout=3, headers=user_agent, allow_redirects=True, stream=True)
    except requests.exceptions.RequestException:
        return False
    if not response.ok or not response.headers.get('Content-Type'):
        return False
    # Content-Type header can return a charset, but we just need the
    # mimetype (eg: image/jpeg;charset=ISO-8859-1)
    content_type = response.headers['Content-Type'].split(';')
    if response.headers['Content-Type'].startswith('image/'):
        return {
            'image_mimetype': content_type[0],
            'og_image': url, # If the url mimetype is already an image type, set url as preview image
            'source_url': url,
        }
    elif response.headers['Content-Type'].startswith('text/html'):
        return get_link_preview_from_html(url, response)
    return False

def get_link_preview_from_html(url, response):
    """
    Retrieve the Open Graph properties from the html page. (https://ogp.me/)
    Load the page with chunks of 8kb to prevent loading the whole
    html when we only need the <head> tag content.
    Fallback on the <title> tag if the html doesn't have
    any Open Graph title property.
    """
    content = b""
    for chunk in response.iter_content(chunk_size=8192):
        content += chunk
        pos = content.find(b'</head>', -8196 * 2)
        # Stop reading once all the <head> data is found
        if pos != -1:
            content = content[:pos + 7]
            break

    if not content:
        return False
    tree = html.fromstring(content)
    og_title = tree.xpath('//meta[@property="og:title"]/@content')
    if og_title:
        og_title = og_title[0]
    elif tree.find('.//title') is not None:
        # Fallback on the <title> tag if it exists
        og_title = tree.find('.//title').text
    else:
        return False
    og_description = tree.xpath('//meta[@property="og:description"]/@content')
    og_type = tree.xpath('//meta[@property="og:type"]/@content')
    og_site_name = tree.xpath('//meta[@property="og:site_name"]/@content')
    og_image = tree.xpath('//meta[@property="og:image"]/@content')
    og_mimetype = tree.xpath('//meta[@property="og:image:type"]/@content')
    return {
        'og_description': og_description[0] if og_description else None,
        'og_image': og_image[0] if og_image else None,
        'og_mimetype': og_mimetype[0] if og_mimetype else None,
        'og_title': og_title,
        'og_type': og_type[0] if og_type else None,
        'og_site_name': og_site_name[0] if og_site_name else None,
        'source_url': url,
    }
