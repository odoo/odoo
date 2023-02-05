# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree, html
import logging
import markupsafe
import re

from bleach import html5lib_shim
from bleach.sanitizer import BleachSanitizerFilter
from odoo.loglevels import ustr


_logger = logging.getLogger(__name__)

SAFE_ATTRIBUTES = {
    'aria-expanded', 'abbr', 'accept', 'accept-charset', 'accesskey', 'action', 'align',
    'alt', 'axis', 'backdropxmlns', 'bgcolor', 'border', 'cellpadding', 'cellspacing',
    'char', 'charoff', 'charset', 'checked', 'cite', 'class', 'clear', 'color', 'cols',
    'colspan', 'compact', 'content', 'contentxmlns', 'coords', 'data-class',
    'data-file-name', 'data-gl-filter', 'data-id', 'data-interval', 'data-member_id',
    'data-mimetype', 'data-o-mail-quote', 'data-o-mail-quote-container',
    'data-o-mail-quote-node', 'data-oe-expression', 'data-oe-field', 'data-oe-id',
    'data-oe-model', 'data-oe-nodeid', 'data-oe-translation-id', 'data-oe-type',
    'data-original-id', 'data-original-mimetype', 'data-original-src', 'data-publish',
    'data-quality', 'data-res_id', 'data-resize-width', 'data-scroll-background-ratio',
    'data-shape', 'data-shape-colors', 'data-view-id', 'data-oe-translation-initial-sha',
    'data-oe-protected',  # editor
    'data-behavior-props', 'data-prop-name',  # knowledge commands
    'datetime', 'dir', 'disabled',
    'enctype', 'equiv', 'face', 'for', 'headers', 'height', 'hidden', 'href', 'hreflang',
    'hspace', 'http-equiv', 'id', 'ismap', 'itemprop', 'itemscope', 'itemtype', 'label',
    'lang', 'loading', 'longdesc', 'maxlength', 'media', 'method', 'multiple', 'name',
    'nohref', 'noshade', 'nowrap', 'prompt', 'readonly', 'rel', 'res_id', 'res_model',
    'rev', 'role', 'rows', 'rowspan', 'rules', 'scope', 'selected', 'shape', 'size',
    'span', 'src', 'start', 'style', 'summary', 'tabindex', 'target', 'text', 'title',
    'token', 'type', 'usemap', 'valign', 'value', 'version', 'vspace', 'widget', 'width',
    'xml:lang', 'xmlns',
}

SAFE_TAGS = {
    'a', 'abbr', 'acronym', 'address', 'applet', 'area', 'article', 'aside',
    'audio', 'b', 'basefont', 'bdi', 'bdo', 'big', 'blink', 'blockquote', 'bodyb',
    'br', 'button', 'c', 'canvas', 'caption', 'center', 'cite', 'code', 'col',
    'colgroup', 'command', 'd', 'datalist', 'dd', 'del', 'details', 'dfn', 'dir',
    'div', 'dl', 'dt', 'e', 'em', 'f', 'fieldset', 'figcaption', 'figure', 'font',
    'footer', 'form', 'frameset', 'h', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header',
    'hgroup', 'hr', 'html', 'i', 'img', 'input', 'ins', 'isindex', 'kbd', 'keygen',
    'l', 'label', 'legend', 'li', 'm', 'main', 'map', 'mark', 'marquee', 'math',
    'menu', 'meter', 'n', 'nav', 'o', 'ol', 'optgroup', 'option', 'output', 'p',
    'param', 'pre', 'progress', 'q', 'role', 'rp', 'rt', 'ruby', 's', 'samp', 'section',
    'select', 'small', 'source', 'span', 'strike', 'strong', 'sub', 'summary', 'sup',
    'svg', 't', 'table', 'tbody', 'td', 'textarea', 'tfoot', 'th', 'thead', 'time',
    'tr', 'track', 'tt', 'u', 'ul', 'var', 'video', 'wbr',
}


# Those tags are removed and their children as well
# If sanitize_tags is False, this list is ignored
KILL_TAGS = {
    'base', 'embed', 'frame', 'head', 'iframe', 'link', 'meta',
    'noscript', 'object', 'script', 'style', 'title',
}

# Those tag are remove even if sanitize_tags is False
CLEAN_TAGS = {
    'meta',
}

STYLE_SAFE_ATTRIBUTES = {
    'background-color', 'color', 'display', 'float', 'font-family', 'font-size', 'font-style',
    'font-weight', 'letter-spacing', 'line-height', 'margin', 'margin-bottom',
    'margin-left', 'margin-right', 'margin-top', 'opacity', 'padding', 'padding-bottom',
    'padding-left', 'padding-right', 'padding-top', 'text-align', 'text-decoration',
    'text-transform', 'vertical-align', 'white-space'
    # box model
    'border', 'border-bottom', 'border-color', 'border-radius', 'border-style',
    'border-top', 'border-width', 'height', 'max-width', 'min-height', 'min-width',
    'width',
    # tables
    'border-collapse', 'border-spacing', 'caption-side',
    'empty-cells', 'table-layout',
    # border style
    *{
        f'border-{position}-{attribute}'
        for position in ('top', 'bottom', 'left', 'right')
        for attribute in ('style', 'color', 'width', 'left-radius', 'right-radius')
    },
}


KILLED_TAG_NAME = '__<killed>__'
re_tag_start = rf'<\s*{KILLED_TAG_NAME}[^>]*>'
re_tag_end = rf'<\/\s*{KILLED_TAG_NAME}\s*>'

re_killed_tag = re.compile(re_tag_start + '.*?' + re_tag_end, re.DOTALL)
re_killed_empty = re.compile(re_tag_start, re.DOTALL)

DATA_ATTRIBUTE_REGEX = re.compile(r'^[a-zA-Z0-9\-_]*$')


class OdooCleaner(BleachSanitizerFilter):
    """HTML cleaner, allow us to have more control on the bleach sanitizer.

    We do not use the standard bleach Cleaner, because we are limited in the
    customization we can make. E.G. the "data:" protocol is blocked for a good reason.
    But it can be useful to embed image "data:image/png;base64,". With the standard
    cleaner, there's no way to check the entire value (we can only allow the entire
    protocol "data:" or block it).

    We also need to strip some elements all their children. E.G. if we remove a
    <style/> tags, we don't want to keep the CSS code in the HTML source.
    """

    def __init__(self, sanitize_tags=True, sanitize_form=True, sanitize_style=False, **kwargs):
        self.sanitize_tags = sanitize_tags
        self.sanitize_form = sanitize_form
        self.sanitize_style = sanitize_style
        super().__init__(**kwargs)

    def sanitize_css(self, style):
        """Disable sanitization of CSS based on self.sanitize_style."""
        if self.sanitize_style:
            return super().sanitize_css(style)

        return style

    def sanitize_token(self, token):
        tag_name = token.get('name', '').lower().strip()
        tag_type = token['type']

        if self.sanitize_form and tag_name == 'form':
            # Ignore sanitize_tags, always remove it
            return self._mark_to_kill(token)

        if self.sanitize_tags and tag_name in KILL_TAGS:
            # We will strip manually those token because
            # bleach will keep the child elements
            return self._mark_to_kill(token)

        if (not self.sanitize_tags
           and tag_type in ('StartTag', 'EmptyTag', 'EndTag')
           and tag_name not in CLEAN_TAGS):
            return self.allow_token(token)

        # Sanitize attributes and tags
        return super().sanitize_token(token)

    def _mark_to_kill(self, token):
        """Kill a token, the element and all its children will be removed.

        We just keep the token type (StartTag, EndTag,...) and use a custom tag name
        to be able to remove it after the bleach sanitization. This is needed because
        bleach only remove the element itself and not its children.

        See https://github.com/mozilla/bleach/issues/67
        See https://github.com/mozilla/bleach/issues/185
        """
        return {
            'name': KILLED_TAG_NAME,
            'type': token['type'],
            'data': {},
        }

    def sanitize_uri_value(self, value, allowed_protocols):
        allowed_data_protocols = (
            'data:image/png;base64,',
            'data:image/jpg;base64,',
            'data:image/jpeg;base64,',
            'data:image/bmp;base64,',
            'data:image/gif;base64,',
        )

        if value.startswith(allowed_data_protocols):
            return value

        return super().sanitize_uri_value(value, allowed_protocols)


def html_sanitize(
    src,
    silent=True,
    sanitize_tags=True,
    restricted_attributes=True,
    sanitize_style=False,
    sanitize_form=True,
    strip_style=False,
    strip_classes=False,
):
    """Sanitize an un-trusted HTML source to be safe from a XSS point of view.

    Automatically close the HTML tags, can remove form, style tags, prevent
    dangling markup, etc...

    Careful if you change one default value, it might create a XSS,
    do not change them if you don't know what you do!

    :param src: HTML string to sanitize
    :param silent: If an error occurs during the parsing, do not raise
        If True, the HTML content is replaced by an error message
    :param sanitize_tags: Allow only an allowed list of HTML tags
    :param restricted_attributes: Allow only an allowed list of attributes
        If False, all data-XXX attributes are already allowed
    :param sanitize_style: Sanitize the style attribute, allow only an allowed list of CSS value
    :param sanitize_form: Remove any <form/> tags
    :param strip_style: Remove any "style" attribute, can not be used when sanitize_style is set
    :param strip_classes: Remove any "class" attribute
    """
    if isinstance(src, bytes):
        src = ustr(src)

    if not src or src.isspace():
        return src

    safe_tag = SAFE_TAGS.copy()
    safe_attributes = SAFE_ATTRIBUTES.copy()

    assert not (
        strip_style and sanitize_style
    ), 'You can not both sanitize and remove the style attributes at the same time.'

    if strip_style:
        safe_attributes.remove('style')
    if strip_classes:
        safe_attributes.remove('class')

    def check_attribute(tag, name, value):
        if not restricted_attributes and name.lower().startswith('data-'):
            return bool(DATA_ATTRIBUTE_REGEX.match(name))
        return name.lower() in safe_attributes

    parser = html5lib_shim.BleachHTMLParser(
        tags=None,
        strip=False,
        consume_entities=False,
        namespaceHTMLElements=False,
    )
    walker = html5lib_shim.getTreeWalker('etree')

    serializer = html5lib_shim.BleachHTMLSerializer(
        quote_attr_values='always',
        omit_optional_tags=False,
        escape_lt_in_attrs=True,
        resolve_entities=False,
        sanitize=False,
        alphabetical_attributes=False,
        minimize_boolean_attributes=False,
        use_trailing_solidus=True,
    )

    try:
        filtered = OdooCleaner(
            source=walker(parser.parseFragment(src)),
            allowed_elements=safe_tag,
            attributes={'*': check_attribute},
            allowed_protocols={
                'http',
                'https',
                'mailto',
                'tel',
                'sms',
                'mid',
                'cid',
            },
            strip_disallowed_elements=True,
            strip_html_comments=True,
            allowed_css_properties=STYLE_SAFE_ATTRIBUTES,
            # Custom arguments
            sanitize_tags=sanitize_tags,
            sanitize_form=sanitize_form,
            sanitize_style=sanitize_style,
        )

        cleaned_src = serializer.render(filtered)

    except Exception:
        if not silent:
            raise

        _logger.warning('unknown error when sanitizing %r', src, exc_info=True)
        cleaned_src = '<p>Unknown error when sanitizing</p>'

    # See OdooCleaner, we need to removed the killed elements
    cleaned_src = re_killed_tag.sub('', cleaned_src)
    cleaned_src = re_killed_empty.sub('', cleaned_src)

    return html_normalize(cleaned_src)


def html_normalize(html_value):
    """Normalize `html_value` for storage as an html field value.

    :param html_value: the html string to normalize
    """
    if not html_value:
        return html_value

    if not html_value or html_value.isspace():
        return html_value

    html_value = html_value.strip()

    if '<p' not in html_value and html_value[0] != '<':
        # ensure that a simple text will be embed into a <p/>
        html_value = f'<p>{html_value}</p>'

    return markupsafe.Markup(html_value)


def html_canonicalize(html_value):
    """Return the canonical form of the HTML value (attributes are sorted, etc)."""
    if not html_value:
        return ''

    # method "c14n" sort XML attributes
    # (encoding is not compatible with canonicalisation)
    result = etree.tostring(html.fromstring(html_value), method='c14n').decode()
    # replace multiple space between tags with a single space
    result = re.sub(r'(>|^)\s+(<|$)', r'\g<1> \g<2>', result)
    return result


def html_compare(source_1, source_2):
    """Compare 2 HTML sources and return True if they are considered as the same."""
    source_1 = html_canonicalize(html_normalize(source_1))
    source_2 = html_canonicalize(html_normalize(source_2))
    return source_1 == source_2
