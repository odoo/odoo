# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import collections
import itertools
import logging
import random
import re
import socket
import time
import email.utils
from email.utils import getaddresses as orig_getaddresses
from urllib.parse import urlparse
import html as htmllib

import idna
import markupsafe
from lxml import etree, html
from lxml.html import clean, defs
from werkzeug import urls

from odoo.tools import misc

__all__ = [
    "email_domain_extract",
    "email_domain_normalize",
    "email_normalize",
    "email_normalize_all",
    "email_split",
    "encapsulate_email",
    "formataddr",
    "html2plaintext",
    "html_normalize",
    "html_sanitize",
    "is_html_empty",
    "parse_contact_from_email",
    "plaintext2html",
    "single_email_re",
]

_logger = logging.getLogger(__name__)


# disable strict mode when present: we rely on original non-strict
# parsing, and we know that it isn't reliable, that ok.
# cfr python/cpython@4a153a1d3b18803a684cd1bcc2cdf3ede3dbae19
if hasattr(email.utils, 'supports_strict_parsing'):
    def getaddresses(fieldvalues):
        return orig_getaddresses(fieldvalues, strict=False)
else:
    getaddresses = orig_getaddresses


#----------------------------------------------------------
# HTML Sanitizer
#----------------------------------------------------------

safe_attrs = defs.safe_attrs | frozenset(
    ['style',
     'data-o-mail-quote', 'data-o-mail-quote-node',  # quote detection
     'data-oe-model', 'data-oe-id', 'data-oe-field', 'data-oe-type', 'data-oe-expression', 'data-oe-translation-source-sha', 'data-oe-nodeid',
     'data-last-history-steps', 'data-oe-protected', 'data-embedded', 'data-embedded-editable', 'data-embedded-props', 'data-oe-version',
     'data-oe-transient-content', 'data-behavior-props', 'data-prop-name', 'data-width', 'data-height', 'data-scale-x', 'data-scale-y', 'data-x', 'data-y',  # legacy editor
     'data-oe-role', 'data-oe-aria-label',
     'data-publish', 'data-id', 'data-res_id', 'data-interval', 'data-member_id', 'data-scroll-background-ratio', 'data-view-id',
     'data-class', 'data-mimetype', 'data-original-src', 'data-original-id', 'data-gl-filter', 'data-quality', 'data-resize-width',
     'data-shape', 'data-shape-colors', 'data-file-name', 'data-original-mimetype',
     'data-mimetype-before-conversion',
     ])
SANITIZE_TAGS = {
    # allow new semantic HTML5 tags
    'allow_tags': defs.tags | frozenset('article bdi section header footer hgroup nav aside figure main'.split() + [etree.Comment]),
    'kill_tags': ['base', 'embed', 'frame', 'head', 'iframe', 'link', 'meta',
                  'noscript', 'object', 'script', 'style', 'title'],
    'remove_tags': ['html', 'body'],
}


class _Cleaner(clean.Cleaner):

    _style_re = re.compile(r'''([\w-]+)\s*:\s*((?:[^;"']|"[^";]*"|'[^';]*')+)''')

    _style_whitelist = [
        'font-size', 'font-family', 'font-weight', 'font-style', 'background-color', 'color', 'text-align',
        'line-height', 'letter-spacing', 'text-transform', 'text-decoration', 'text-decoration', 'opacity',
        'float', 'vertical-align', 'display', 'object-fit',
        'padding', 'padding-top', 'padding-left', 'padding-bottom', 'padding-right',
        'margin', 'margin-top', 'margin-left', 'margin-bottom', 'margin-right',
        'white-space',
        # appearance
        'background-image', 'background-position', 'background-size', 'background-repeat', 'background-origin',
        # box model
        'border', 'border-color', 'border-radius', 'border-style', 'border-width', 'border-top', 'border-bottom',
        'height', 'width', 'max-width', 'min-width', 'min-height',
        # tables
        'border-collapse', 'border-spacing', 'caption-side', 'empty-cells', 'table-layout']

    _style_whitelist.extend(
        ['border-%s-%s' % (position, attribute)
            for position in ['top', 'bottom', 'left', 'right']
            for attribute in ('style', 'color', 'width', 'left-radius', 'right-radius')]
    )

    strip_classes = False
    sanitize_style = False
    conditional_comments = True

    def __call__(self, doc):
        super(_Cleaner, self).__call__(doc)

        # if we keep attributes but still remove classes
        if not getattr(self, 'safe_attrs_only', False) and self.strip_classes:
            for el in doc.iter(tag=etree.Element):
                self.strip_class(el)

        # if we keep style attribute, sanitize them
        if not self.style and self.sanitize_style:
            for el in doc.iter(tag=etree.Element):
                self.parse_style(el)

    def strip_class(self, el):
        if el.attrib.get('class'):
            del el.attrib['class']

    def parse_style(self, el):
        attributes = el.attrib
        styling = attributes.get('style')
        if styling:
            valid_styles = collections.OrderedDict()
            styles = self._style_re.findall(styling)
            for style in styles:
                if style[0].lower() in self._style_whitelist:
                    valid_styles[style[0].lower()] = style[1]
            if valid_styles:
                el.attrib['style'] = '; '.join('%s:%s' % (key, val) for (key, val) in valid_styles.items())
            else:
                del el.attrib['style']

    def kill_conditional_comments(self, doc):
        """Override the default behavior of lxml.

        https://github.com/lxml/lxml/blob/e82c9153c4a7d505480b94c60b9a84d79d948efb/src/lxml/html/clean.py#L501-L510

        In some use cases, e.g. templates used for mass mailing,
        we send emails containing conditional comments targeting Microsoft Outlook,
        to give special styling instructions.
        https://github.com/odoo/odoo/pull/119325/files#r1301064789

        Within these conditional comments, unsanitized HTML can lie.
        However, in modern browser, these comments are considered as simple comments,
        their content is not executed.
        https://caniuse.com/sr_ie-features
        """
        if self.conditional_comments:
            super().kill_conditional_comments(doc)


def tag_quote(el):
    def _create_new_node(tag, text, tail=None, attrs=None):
        new_node = etree.Element(tag)
        new_node.text = text
        new_node.tail = tail
        if attrs:
            for key, val in attrs.items():
                new_node.set(key, val)
        return new_node

    def _tag_matching_regex_in_text(regex, node, tag='span', attrs=None):
        text = node.text or ''
        if not re.search(regex, text):
            return

        child_node = None
        idx, node_idx = 0, 0
        for item in re.finditer(regex, text):
            new_node = _create_new_node(tag, text[item.start():item.end()], None, attrs)
            if child_node is None:
                node.text = text[idx:item.start()]
                new_node.tail = text[item.end():]
                node.insert(node_idx, new_node)
            else:
                child_node.tail = text[idx:item.start()]
                new_node.tail = text[item.end():]
                node.insert(node_idx, new_node)
            child_node = new_node
            idx = item.end()
            node_idx = node_idx + 1

    el_class = el.get('class', '') or ''
    el_id = el.get('id', '') or ''

    # gmail or yahoo // # outlook, html // # msoffice
    if 'gmail_extra' in el_class or \
            ('SkyDrivePlaceholder' in el_class or 'SkyDrivePlaceholder' in el_class):
        el.set('data-o-mail-quote', '1')
        if el.getparent() is not None:
            el.getparent().set('data-o-mail-quote-container', '1')

    if (el.tag == 'hr' and ('stopSpelling' in el_class or 'stopSpelling' in el_id)) or \
       'yahoo_quoted' in el_class:
        # Quote all elements after this one
        el.set('data-o-mail-quote', '1')
        for sibling in el.itersiblings(preceding=False):
            sibling.set('data-o-mail-quote', '1')

    # odoo, gmail and outlook automatic signature wrapper
    is_signature_wrapper = 'odoo_signature_wrapper' in el_class or 'gmail_signature' in el_class or el_id == "Signature"
    is_outlook_auto_message = 'appendonsend' in el_id
    # gmail and outlook reply quote
    is_outlook_reply_quote = 'divRplyFwdMsg' in el_id
    is_gmail_quote = 'gmail_quote' in el_class
    is_quote_wrapper = is_signature_wrapper or is_gmail_quote or is_outlook_reply_quote
    if is_quote_wrapper:
        el.set('data-o-mail-quote-container', '1')
        el.set('data-o-mail-quote', '1')

    # outlook reply wrapper is preceded with <hr> and a div containing recipient info
    if is_outlook_reply_quote:
        hr = el.getprevious()
        reply_quote = el.getnext()
        if hr is not None and hr.tag == 'hr':
            hr.set('data-o-mail-quote', '1')
        if reply_quote is not None:
            reply_quote.set('data-o-mail-quote-container', '1')
            reply_quote.set('data-o-mail-quote', '1')

    if is_outlook_auto_message:
        if not el.text or not el.text.strip():
            el.set('data-o-mail-quote-container', '1')
            el.set('data-o-mail-quote', '1')

    # html signature (-- <br />blah)
    signature_begin = re.compile(r"((?:(?:^|\n)[-]{2}[\s]?$))")
    if el.text and el.find('br') is not None and re.search(signature_begin, el.text):
        el.set('data-o-mail-quote', '1')
        if el.getparent() is not None:
            el.getparent().set('data-o-mail-quote-container', '1')

    # text-based quotes (>, >>) and signatures (-- Signature)
    text_complete_regex = re.compile(r"((?:\n[>]+[^\n\r]*)+|(?:(?:^|\n)[-]{2}[\s]?[\r\n]{1,2}[\s\S]+))")
    if not el.get('data-o-mail-quote'):
        _tag_matching_regex_in_text(text_complete_regex, el, 'span', {'data-o-mail-quote': '1'})

    if el.tag == 'blockquote':
        # remove single node
        el.set('data-o-mail-quote-node', '1')
        el.set('data-o-mail-quote', '1')
    if el.getparent() is not None and not el.getparent().get('data-o-mail-quote-node'):
        if el.getparent().get('data-o-mail-quote'):
            el.set('data-o-mail-quote', '1')
        # only quoting the elements following the first quote in the container
        # avoids issues with repeated calls to html_normalize
        elif el.getparent().get('data-o-mail-quote-container'):
            if (first_sibling_quote := el.getparent().find("*[@data-o-mail-quote]")) is not None:
                siblings = el.getparent().getchildren()
                quote_index = siblings.index(first_sibling_quote)
                element_index = siblings.index(el)
                if quote_index < element_index:
                    el.set('data-o-mail-quote', '1')
    if el.getprevious() is not None and el.getprevious().get('data-o-mail-quote') and not el.text_content().strip():
        el.set('data-o-mail-quote', '1')


def html_normalize(src, filter_callback=None, output_method="html"):
    """ Normalize `src` for storage as an html field value.

    The string is parsed as an html tag soup, made valid, then decorated for
    "email quote" detection, and prepared for an optional filtering.
    The filtering step (e.g. sanitization) should be performed by the
    `filter_callback` function (to avoid multiple parsing operations, and
    normalize the result).

    :param src: the html string to normalize
    :param filter_callback: optional callable taking a single `etree._Element`
        document parameter, to be called during normalization in order to
        filter the output document
    :param output_method: defines the output method to pass to `html.tostring`.
        It defaults to 'html', but can also be 'xml' for xhtml output.
    """
    if not src:
        return src

    # html: remove encoding attribute inside tags
    src = re.sub(r'(<[^>]*\s)(encoding=(["\'][^"\']*?["\']|[^\s\n\r>]+)(\s[^>]*|/)?>)', "", src, flags=re.IGNORECASE | re.DOTALL)

    src = src.replace('--!>', '-->')
    src = re.sub(r'(<!-->|<!--->)', '<!-- -->', src)
    # On the specific case of Outlook desktop it adds unnecessary '<o:.*></o:.*>' tags which are parsed
    # in '<p></p>' which may alter the appearance (eg. spacing) of the mail body
    src = re.sub(r'</?o:.*?>', '', src)

    try:
        doc = html.fromstring(src)
    except etree.ParserError as e:
        # HTML comment only string, whitespace only..
        if 'empty' in str(e):
            return ""
        raise

    # perform quote detection before cleaning and class removal
    if doc is not None:
        for el in doc.iter(tag=etree.Element):
            tag_quote(el)

    if filter_callback:
        doc = filter_callback(doc)

    src = html.tostring(doc, encoding='unicode', method=output_method)

    # this is ugly, but lxml/etree tostring want to put everything in a
    # 'div' that breaks the editor -> remove that
    if src.startswith('<div>') and src.endswith('</div>'):
        src = src[5:-6]

    # html considerations so real html content match database value
    src = src.replace(u'\xa0', u'&nbsp;')

    return src


def html_sanitize(src, silent=True, sanitize_tags=True, sanitize_attributes=False, sanitize_style=False, sanitize_form=True, sanitize_conditional_comments=True, strip_style=False, strip_classes=False, output_method="html"):
    if not src:
        return src

    logger = logging.getLogger(__name__ + '.html_sanitize')

    def sanitize_handler(doc):
        kwargs = {
            'page_structure': True,
            'style': strip_style,              # True = remove style tags/attrs
            'sanitize_style': sanitize_style,  # True = sanitize styling
            'forms': sanitize_form,            # True = remove form tags
            'remove_unknown_tags': False,
            'comments': False,
            'conditional_comments': sanitize_conditional_comments,   # True = remove conditional comments
            'processing_instructions': False
        }
        if sanitize_tags:
            kwargs.update(SANITIZE_TAGS)

        if sanitize_attributes:  # We keep all attributes in order to keep "style"
            if strip_classes:
                current_safe_attrs = safe_attrs - frozenset(['class'])
            else:
                current_safe_attrs = safe_attrs
            kwargs.update({
                'safe_attrs_only': True,
                'safe_attrs': current_safe_attrs,
            })
        else:
            kwargs.update({
                'safe_attrs_only': False,  # keep oe-data attributes + style
                'strip_classes': strip_classes,  # remove classes, even when keeping other attributes
            })

        cleaner = _Cleaner(**kwargs)
        cleaner(doc)
        return doc

    try:
        sanitized = html_normalize(src, filter_callback=sanitize_handler, output_method=output_method)
    except etree.ParserError:
        if not silent:
            raise
        logger.warning(u'ParserError obtained when sanitizing %r', src, exc_info=True)
        sanitized = '<p>ParserError when sanitizing</p>'
    except Exception:
        if not silent:
            raise
        logger.warning(u'unknown error obtained when sanitizing %r', src, exc_info=True)
        sanitized = '<p>Unknown error when sanitizing</p>'

    return markupsafe.Markup(sanitized)

# ----------------------------------------------------------
# HTML/Text management
# ----------------------------------------------------------

URL_SKIP_PROTOCOL_REGEX = r'mailto:|tel:|sms:'
URL_REGEX = rf'''(\bhref=['"](?!{URL_SKIP_PROTOCOL_REGEX})([^'"]+)['"])'''
TEXT_URL_REGEX = r'https?://[\w@:%.+&~#=/-]+(?:\?\S+)?'
# retrieve inner content of the link
HTML_TAG_URL_REGEX = URL_REGEX + r'([^<>]*>([^<>]+)<\/)?'
HTML_TAGS_REGEX = re.compile('<.*?>')
HTML_NEWLINES_REGEX = re.compile('<(div|p|br|tr)[^>]*>|\n')


def validate_url(url):
    if urls.url_parse(url).scheme not in ('http', 'https', 'ftp', 'ftps'):
        return 'http://' + url

    return url


def is_html_empty(html_content):
    """Check if a html content is empty. If there are only formatting tags with style
    attributes or a void content  return True. Famous use case if a
    '<p style="..."><br></p>' added by some web editor.

    :param str html_content: html content, coming from example from an HTML field
    :returns: bool, True if no content found or if containing only void formatting tags
    """
    if not html_content:
        return True
    icon_re = r'<\s*(i|span)\b(\s+[A-Za-z_-][A-Za-z0-9-_]*(\s*=\s*[\'"][^"\']*[\'"])?)*\s*\bclass\s*=\s*["\'][^"\']*\b(fa|fab|fad|far|oi)\b'
    tag_re = r'<\s*\/?(?:p|div|section|span|br|b|i|font)\b(?:(\s+[A-Za-z_-][A-Za-z0-9-_]*(\s*=\s*[\'"][^"\']*[\'"]))*)(?:\s*>|\s*\/\s*>)'
    return not bool(re.sub(tag_re, '', html_content).strip()) and not re.search(icon_re, html_content)


def html_keep_url(text):
    """ Transform the url into clickable link with <a/> tag """
    idx = 0
    final = ''
    link_tags = re.compile(r"""(?<!["'])((ftp|http|https):\/\/(\w+:{0,1}\w*@)?([^\s<"']+)(:[0-9]+)?(\/|\/([^\s<"']))?)(?![^\s<"']*["']|[^\s<"']*</a>)""")
    for item in re.finditer(link_tags, text):
        final += text[idx:item.start()]
        final += create_link(item.group(0), item.group(0))
        idx = item.end()
    final += text[idx:]
    return final


def html_to_inner_content(html):
    """Returns unformatted text after removing html tags and excessive whitespace from a
    string/Markup. Passed strings will first be sanitized.
    """
    if is_html_empty(html):
        return ''
    if not isinstance(html, markupsafe.Markup):
        html = html_sanitize(html)
    processed = re.sub(HTML_NEWLINES_REGEX, ' ', html)
    processed = re.sub(HTML_TAGS_REGEX, '', processed)
    processed = re.sub(r' {2,}|\t', ' ', processed)
    processed = htmllib.unescape(processed)
    processed = processed.strip()
    return processed


def create_link(url, label):
    return f'<a href="{url}" target="_blank" rel="noreferrer noopener">{label}</a>'


def html2plaintext(html, body_id=None, encoding='utf-8', include_references=True):
    """ From an HTML text, convert the HTML to plain text.
    If @param body_id is provided then this is the tag where the
    body (not necessarily <body>) starts.
    :param include_references: If False, numbered references and
        URLs for links and images will not be included.
    """
    ## (c) Fry-IT, www.fry-it.com, 2007
    ## <peter@fry-it.com>
    ## download here: http://www.peterbe.com/plog/html2plaintext
    if not (html and html.strip()):
        return ''

    if isinstance(html, bytes):
        html = html.decode(encoding)
    else:
        assert isinstance(html, str), f"expected str got {html.__class__.__name__}"

    tree = etree.fromstring(html, parser=etree.HTMLParser())

    if body_id is not None:
        source = tree.xpath('//*[@id=%s]' % (body_id,))
    else:
        source = tree.xpath('//body')
    if len(source):
        tree = source[0]

    url_index = []
    linkrefs = itertools.count(1)
    if include_references:
        for link in tree.findall('.//a'):
            if url := link.get('href'):
                link.tag = 'span'
                link.text = f'{link.text} [{next(linkrefs)}]'
                url_index.append(url)

        for img in tree.findall('.//img'):
            if src := img.get('src'):
                img.tag = 'span'
                if src.startswith('data:'):
                    img_name = None  # base64 image
                else:
                    img_name = re.search(r'[^/]+(?=\.[a-zA-Z]+(?:\?|$))', src)
                img.text = '%s [%s]' % (img_name[0] if img_name else 'Image', next(linkrefs))
                url_index.append(src)

    html = etree.tostring(tree, encoding="unicode")
    # \r char is converted into &#13;, must remove it
    html = html.replace('&#13;', '')

    html = html.replace('<strong>', '*').replace('</strong>', '*')
    html = html.replace('<b>', '*').replace('</b>', '*')
    html = html.replace('<h3>', '*').replace('</h3>', '*')
    html = html.replace('<h2>', '**').replace('</h2>', '**')
    html = html.replace('<h1>', '**').replace('</h1>', '**')
    html = html.replace('<em>', '/').replace('</em>', '/')
    html = html.replace('<tr>', '\n')
    html = html.replace('</p>', '\n')
    html = re.sub(r'<br\s*/?>', '\n', html)
    html = re.sub('<.*?>', ' ', html)
    html = html.replace(' ' * 2, ' ')
    html = html.replace('&gt;', '>')
    html = html.replace('&lt;', '<')
    html = html.replace('&amp;', '&')
    html = html.replace('&nbsp;', '\N{NO-BREAK SPACE}')

    # strip all lines
    html = '\n'.join([x.strip() for x in html.splitlines()])
    html = html.replace('\n' * 2, '\n')

    if url_index:
        html += '\n\n'
        for i, url in enumerate(url_index, start=1):
            html += f'[{i}] {url}\n'

    return html.strip()

def plaintext2html(text, container_tag=None):
    r"""Convert plaintext into html. Content of the text is escaped to manage
    html entities, using :func:`~odoo.tools.misc.html_escape`.

    - all ``\n``, ``\r`` are replaced by ``<br/>``
    - enclose content into ``<p>``
    - convert url into clickable link
    - 2 or more consecutive ``<br/>`` are considered as paragraph breaks

    :param str text: plaintext to convert
    :param str container_tag: container of the html; by default the content is
        embedded into a ``<div>``
    :rtype: markupsafe.Markup
    """
    assert isinstance(text, str)
    text = misc.html_escape(text)

    # 1. replace \n and \r
    text = re.sub(r'(\r\n|\r|\n)', '<br/>', text)

    # 2. clickable links
    text = html_keep_url(text)

    # 3-4: form paragraphs
    idx = 0
    final = '<p>'
    br_tags = re.compile(r'(([<]\s*[bB][rR]\s*/?[>]\s*){2,})')
    for item in re.finditer(br_tags, text):
        final += text[idx:item.start()] + '</p><p>'
        idx = item.end()
    final += text[idx:] + '</p>'

    # 5. container
    if container_tag: # FIXME: validate that container_tag is just a simple tag?
        final = '<%s>%s</%s>' % (container_tag, final, container_tag)
    return markupsafe.Markup(final)

def append_content_to_html(html, content, plaintext=True, preserve=False, container_tag=None):
    """ Append extra content at the end of an HTML snippet, trying
        to locate the end of the HTML document (</body>, </html>, or
        EOF), and converting the provided content in html unless ``plaintext``
        is ``False``.

        Content conversion can be done in two ways:

        - wrapping it into a pre (``preserve=True``)
        - use plaintext2html (``preserve=False``, using ``container_tag`` to
          wrap the whole content)

        A side-effect of this method is to coerce all HTML tags to
        lowercase in ``html``, and strip enclosing <html> or <body> tags in
        content if ``plaintext`` is False.

        :param str html: html tagsoup (doesn't have to be XHTML)
        :param str content: extra content to append
        :param bool plaintext: whether content is plaintext and should
            be wrapped in a <pre/> tag.
        :param bool preserve: if content is plaintext, wrap it into a <pre>
            instead of converting it into html
        :param str container_tag: tag to wrap the content into, defaults to `div`.
        :rtype: markupsafe.Markup
    """
    if plaintext and preserve:
        content = '\n<pre>%s</pre>\n' % misc.html_escape(content)
    elif plaintext:
        content = '\n%s\n' % plaintext2html(content, container_tag)
    else:
        content = re.sub(r'(?i)(</?(?:html|body|head|!\s*DOCTYPE)[^>]*>)', '', content)
        content = '\n%s\n' % content
    # Force all tags to lowercase
    html = re.sub(r'(</?)(\w+)([ >])',
        lambda m: '%s%s%s' % (m[1], m[2].lower(), m[3]), html)
    insert_location = html.find('</body>')
    if insert_location == -1:
        insert_location = html.find('</html>')
    if insert_location == -1:
        return markupsafe.Markup('%s%s' % (html, content))
    return markupsafe.Markup('%s%s%s' % (html[:insert_location], content, html[insert_location:]))


def prepend_html_content(html_body, html_content):
    """Prepend some HTML content at the beginning of an other HTML content."""
    replacement = re.sub(r'(?i)(</?(?:html|body|head|!\s*DOCTYPE)[^>]*>)', '', html_content)
    html_content = markupsafe.Markup(replacement) if isinstance(html_content, markupsafe.Markup) else replacement
    html_content = html_content.strip()

    body_match = re.search(r'<body[^>]*>', html_body) or re.search(r'<html[^>]*>', html_body)
    insert_index = body_match.end() if body_match else 0

    return html_body[:insert_index] + html_content + html_body[insert_index:]

#----------------------------------------------------------
# Emails
#----------------------------------------------------------

# matches any email in a body of text
email_re = re.compile(r"""([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63})""", re.VERBOSE)

# matches a string containing only one email
single_email_re = re.compile(r"""^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}$""", re.VERBOSE)

mail_header_msgid_re = re.compile('<[^<>]+>')

email_addr_escapes_re = re.compile(r'[\\"]')

def generate_tracking_message_id(res_id):
    """Returns a string that can be used in the Message-ID RFC822 header field

       Used to track the replies related to a given object thanks to the "In-Reply-To"
       or "References" fields that Mail User Agents will set.
    """
    try:
        rnd = random.SystemRandom().random()
    except NotImplementedError:
        rnd = random.random()
    rndstr = ("%.15f" % rnd)[2:]
    return "<%s.%.15f-openerp-%s@%s>" % (rndstr, time.time(), res_id, socket.gethostname())

def email_split_tuples(text):
    """ Return a list of (name, email) address tuples found in ``text`` . Note
    that text should be an email header or a stringified email list as it may
    give broader results than expected on actual text. """
    def _parse_based_on_spaces(pair):
        """ With input 'name email@domain.com' (missing quotes for a formatting)
        getaddresses returns ('', 'name email@domain.com). This when having no
        name and an email a fallback to enhance parsing is to redo a getaddresses
        by replacing spaces by commas. The new email will be split into sub pairs
        allowing to find the email and name parts, allowing to make a new name /
        email pair. Emails should not contain spaces thus this is coherent with
        email formation. """
        name, email = pair
        if not name and email and ' ' in email:
            inside_pairs = getaddresses([email.replace(' ', ',')])
            name_parts, found_email = [], False
            for pair in inside_pairs:
                if pair[1] and '@' not in pair[1]:
                    name_parts.append(pair[1])
                if pair[1] and '@' in pair[1]:
                    found_email = pair[1]
            name, email = (' '.join(name_parts), found_email) if found_email else (name, email)
        return (name, email)

    if not text:
        return []

    # found valid pairs, filtering out failed parsing
    valid_pairs = [
        (addr[0], addr[1]) for addr in getaddresses([text])
        # getaddresses() returns '' when email parsing fails, and
        # sometimes returns emails without at least '@'. The '@'
        # is strictly required in RFC2822's `addr-spec`.
        if addr[1] and '@' in addr[1]
    ]
    # corner case: returning '@gmail.com'-like email (see test_email_split)
    if any(pair[1].startswith('@') for pair in valid_pairs):
        filtered = [
            found_email for found_email in email_re.findall(text)
            if found_email and not found_email.startswith('@')
        ]
        if filtered:
            valid_pairs = [('', found_email) for found_email in filtered]

    return list(map(_parse_based_on_spaces, valid_pairs))

def email_split(text):
    """ Return a list of the email addresses found in ``text`` """
    if not text:
        return []
    return [email for (name, email) in email_split_tuples(text)]

def email_split_and_format(text):
    """ Return a list of email addresses found in ``text``, formatted using
    formataddr. """
    if not text:
        return []
    return [formataddr((name, email)) for (name, email) in email_split_tuples(text)]

def email_split_and_format_normalize(text):
    """ Same as 'email_split_and_format' but normalizing email. """
    return [
        formataddr(
            (name, _normalize_email(email))
        ) for (name, email) in email_split_tuples(text)
    ]

def email_normalize(text, strict=True):
    """ Sanitize and standardize email address entries. As of rfc5322 section
    3.4.1 local-part is case-sensitive. However most main providers do consider
    the local-part as case insensitive. With the introduction of smtp-utf8
    within odoo, this assumption is certain to fall short for international
    emails. We now consider that

      * if local part is ascii: normalize still 'lower' ;
      * else: use as it, SMTP-UF8 is made for non-ascii local parts;

    Concerning domain part of the address, as of v14 international domain (IDNA)
    are handled fine. The domain is always lowercase, lowering it is fine as it
    is probably an error. With the introduction of IDNA, there is an encoding
    that allow non-ascii characters to be encoded to ascii ones, using 'idna.encode'.

    A normalized email is considered as :
    - having a left part + @ + a right part (the domain can be without '.something')
    - having no name before the address. Typically, having no 'Name <>'
    Ex:
    - Possible Input Email : 'Name <NaMe@DoMaIn.CoM>'
    - Normalized Output Email : 'name@domain.com'

    :param boolean strict: if True, text should contain a single email
      (default behavior in stable 14+). If more than one email is found no
      normalized email is returned. If False the first found candidate is used
      e.g. if email is 'tony@e.com, "Tony2" <tony2@e.com>', result is either
      False (strict=True), either 'tony@e.com' (strict=False).

    :return: False if no email found (or if more than 1 email found when being
      in strict mode); normalized email otherwise;
    """
    emails = email_split(text)
    if not emails or (strict and len(emails) != 1):
        return False

    return _normalize_email(emails[0])

def email_normalize_all(text):
    """ Tool method allowing to extract email addresses from a text input and returning
    normalized version of all found emails. If no email is found, a void list
    is returned.

    e.g. if email is 'tony@e.com, "Tony2" <tony2@e.com' returned result is ['tony@e.com, tony2@e.com']

    :return list: list of normalized emails found in text
    """
    if not text:
        return []
    emails = email_split(text)
    return list(filter(None, [_normalize_email(email) for email in emails]))

def _normalize_email(email):
    """ As of rfc5322 section 3.4.1 local-part is case-sensitive. However most
    main providers do consider the local-part as case insensitive. With the
    introduction of smtp-utf8 within odoo, this assumption is certain to fall
    short for international emails. We now consider that

      * if local part is ascii: normalize still 'lower' ;
      * else: use as it, SMTP-UF8 is made for non-ascii local parts;

    Concerning domain part of the address, as of v14 international domain (IDNA)
    are handled fine. The domain is always lowercase, lowering it is fine as it
    is probably an error. With the introduction of IDNA, there is an encoding
    that allow non-ascii characters to be encoded to ascii ones, using 'idna.encode'.

    A normalized email is considered as :
    - having a left part + @ + a right part (the domain can be without '.something')
    - having no name before the address. Typically, having no 'Name <>'
    Ex:
    - Possible Input Email : 'Name <NaMe@DoMaIn.CoM>'
    - Normalized Output Email : 'name@domain.com'
    """
    local_part, at, domain = email.rpartition('@')
    try:
        local_part.encode('ascii')
    except UnicodeEncodeError:
        pass
    else:
        local_part = local_part.lower()
    return local_part + at + domain.lower()

def email_anonymize(normalized_email, *, redact_domain=False):
    """
    Replace most charaters in the local part of the email address with
    '*' to hide the recipient, but keep enough characters for debugging
    purpose.

    The email address must be normalized already.

    >>> email_anonymize('admin@example.com')
    'a****@example.com'
    >>> email_anonymize('portal@example.com')
    'p***al@example.com'
    >>> email_anonymize('portal@example.com', redact_domain=True)
    'p***al@e******.com'
    """
    if not normalized_email:
        return normalized_email

    local, at, domain = normalized_email.partition('@')
    if len(local) <= 5:
        anon_local = local[:1] + '*' * (len(local) - 1)
    else:
        anon_local = local[:1] + '*' * (len(local) - 3) + local[-2:]

    host, dot, tld = domain.rpartition('.')
    if redact_domain and not domain.startswith('[') and all((host, dot, tld)):
        anon_host = host[0] + '*' * (len(host) - 1)
    else:
        anon_host = host

    return f'{anon_local}{at}{anon_host}{dot}{tld}'

def email_domain_extract(email):
    """ Extract the company domain to be used by IAP services notably. Domain
    is extracted from email information e.g:

    - info@proximus.be -> proximus.be
    """
    normalized_email = email_normalize(email)
    if normalized_email:
        return normalized_email.split('@')[1]
    return False

def email_domain_normalize(domain):
    """Return the domain normalized or False if the domain is invalid."""
    if not domain or '@' in domain:
        return False

    return domain.lower()

def url_domain_extract(url):
    """ Extract the company domain to be used by IAP services notably. Domain
    is extracted from an URL e.g:

    - www.info.proximus.be -> proximus.be
    """
    parser_results = urlparse(url)
    company_hostname = parser_results.hostname
    if company_hostname and '.' in company_hostname:
        return '.'.join(company_hostname.split('.')[-2:])  # remove subdomains
    return False

def email_escape_char(email_address):
    """ Escape problematic characters in the given email address string"""
    return email_address.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

# was mail_thread.decode_header()
def decode_message_header(message, header, separator=' '):
    return separator.join(h for h in message.get_all(header, []) if h)

def formataddr(pair, charset='utf-8'):
    """Pretty format a 2-tuple of the form (realname, email_address).

    If the first element of pair is falsy then only the email address
    is returned.

    Set the charset to ascii to get a RFC-2822 compliant email. The
    realname will be base64 encoded (if necessary) and the domain part
    of the email will be punycode encoded (if necessary). The local part
    is left unchanged thus require the SMTPUTF8 extension when there are
    non-ascii characters.

    >>> formataddr(('John Doe', 'johndoe@example.com'))
    '"John Doe" <johndoe@example.com>'

    >>> formataddr(('', 'johndoe@example.com'))
    'johndoe@example.com'
    """
    name, address = pair
    local, _, domain = address.rpartition('@')

    try:
        domain.encode(charset)
    except UnicodeEncodeError:
        # rfc5890 - Internationalized Domain Names for Applications (IDNA)
        domain = idna.encode(domain).decode('ascii')

    if name:
        try:
            name.encode(charset)
        except UnicodeEncodeError:
            # charset mismatch, encode as utf-8/base64
            # rfc2047 - MIME Message Header Extensions for Non-ASCII Text
            name = base64.b64encode(name.encode('utf-8')).decode('ascii')
            return f"=?utf-8?b?{name}?= <{local}@{domain}>"
        else:
            # ascii name, escape it if needed
            # rfc2822 - Internet Message Format
            #   #section-3.4 - Address Specification
            name = email_addr_escapes_re.sub(r'\\\g<0>', name)
            return f'"{name}" <{local}@{domain}>'
    return f"{local}@{domain}"

def encapsulate_email(old_email, new_email):
    """Change the FROM of the message and use the old one as name.

    e.g.
    * Old From: "Admin" <admin@gmail.com>
    * New From: notifications@odoo.com
    * Output: "Admin" <notifications@odoo.com>
    """
    old_email_split = getaddresses([old_email])
    if not old_email_split or not old_email_split[0]:
        return old_email

    new_email_split = getaddresses([new_email])
    if not new_email_split or not new_email_split[0]:
        return

    old_name, old_email = old_email_split[0]
    if old_name:
        name_part = old_name
    else:
        name_part = old_email.split("@")[0]

    return formataddr((
        name_part,
        new_email_split[0][1],
    ))

def parse_contact_from_email(text):
    """ Parse contact name and email (given by text) in order to find contact
    information, able to populate records like partners, leads, ...
    Supported syntax:

      * Raoul <raoul@grosbedon.fr>
      * "Raoul le Grand" <raoul@grosbedon.fr>
      * Raoul raoul@grosbedon.fr (strange fault tolerant support from
        df40926d2a57c101a3e2d221ecfd08fbb4fea30e now supported directly
        in 'email_split_tuples';

    Otherwise: default, text is set as name.

    :return: name, email (normalized if possible)
    """
    if not text or not text.strip():
        return '', ''
    split_results = email_split_tuples(text)
    name, email = split_results[0] if split_results else ('', '')

    if email:
        email_normalized = email_normalize(email, strict=False) or email
    else:
        name, email_normalized = text, ''

    return name, email_normalized

def unfold_references(msg_references):
    """ As it declared in [RFC2822] long header bodies can be "folded" using
    CRLF+WSP. Some mail clients split References header body which contains
    Message Ids by "\n ".

    RFC2882: https://tools.ietf.org/html/rfc2822#section-2.2.3 """
    return [
        re.sub(r'[\r\n\t ]+', r'', ref)  # "Unfold" buggy references
        for ref in mail_header_msgid_re.findall(msg_references)
    ]
