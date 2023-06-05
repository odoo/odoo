# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=unused-import

# FIXME: Replace all the import ocurrences by the real locations
from odoo.tests.common import MockRequest
from odoo.tools.mail import text_from_html
from odoo.tools.misc import distance, similarity_score
import werkzeug.urls


def get_base_domain(url, strip_www=False):
    """
    Returns the domain of a given url without the scheme and the www. and the
    final '/' if any.

    :param url: url from which the domain must be extracted
    :param strip_www: if True, strip the www. from the domain

    :return: domain of the url
    """
    if not url:
        return ''

    url = werkzeug.urls.url_parse(url).netloc
    if strip_www and url.startswith('www.'):
        url = url[4:]
    return url
