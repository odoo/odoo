# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import logging
from lxml.html import clean
import random
import re
import socket
import threading
import time

from email.header import decode_header, Header
from email.utils import getaddresses, formataddr
from lxml import etree

import odoo
from odoo.loglevels import ustr
from odoo.tools import pycompat, misc

_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# HTML Sanitizer
#----------------------------------------------------------

tags_to_kill = ["script", "head", "meta", "title", "link", "style", "frame", "iframe", "base", "object", "embed"]
tags_to_remove = ['html', 'body']

# allow new semantic HTML5 tags
allowed_tags = clean.defs.tags | frozenset('article section header footer hgroup nav aside figure main'.split() + [etree.Comment])
safe_attrs = clean.defs.safe_attrs | frozenset(
    ['style',
     'data-o-mail-quote',  # quote detection
     'data-oe-model', 'data-oe-id', 'data-oe-field', 'data-oe-type', 'data-oe-expression', 'data-oe-translation-id', 'data-oe-nodeid',
     'data-publish', 'data-id', 'data-res_id', 'data-member_id', 'data-view-id'
     ])


class _Cleaner(clean.Cleaner):

    _style_re = re.compile('''([\w-]+)\s*:\s*((?:[^;"']|"[^"]*"|'[^']*')+)''')

    _style_whitelist = [
        'font-size', 'font-family', 'font-weight', 'background-color', 'color', 'text-align',
        'line-height', 'letter-spacing', 'text-transform', 'text-decoration',
        'float', 'vertical-align',
        'padding', 'padding-top', 'padding-left', 'padding-bottom', 'padding-right',
        'margin', 'margin-top', 'margin-left', 'margin-bottom', 'margin-right',
        # box model
        'border', 'border-color', 'border-radius', 'border-style', 'border-width',
        'height', 'margin', 'padding', 'width', 'max-width', 'min-width',
        # tables
        'border-collapse', 'border-spacing', 'caption-side', 'empty-cells', 'table-layout']

    _style_whitelist.extend(
        ['border-%s-%s' % (position, attribute)
            for position in ['top', 'bottom', 'left', 'right']
            for attribute in ('style', 'color', 'width', 'left-radius', 'right-radius')]
    )

    strip_classes = False
    sanitize_style = False

    def __call__(self, doc):
        # perform quote detection before cleaning and class removal
        for el in doc.iter(tag=etree.Element):
            self.tag_quote(el)

        super(_Cleaner, self).__call__(doc)

        # if we keep attributes but still remove classes
        if not getattr(self, 'safe_attrs_only', False) and self.strip_classes:
            for el in doc.iter(tag=etree.Element):
                self.strip_class(el)

        # if we keep style attribute, sanitize them
        if not self.style and self.sanitize_style:
            for el in doc.iter(tag=etree.Element):
                self.parse_style(el)

    def tag_quote(self, el):
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
        if ('gmail_extra' in el_class or 'yahoo_quoted' in el_class) or \
                (el.tag == 'hr' and ('stopSpelling' in el_class or 'stopSpelling' in el_id)) or \
                ('SkyDrivePlaceholder' in el_class or 'SkyDrivePlaceholder' in el_class):
            el.set('data-o-mail-quote', '1')
            if el.getparent() is not None:
                el.getparent().set('data-o-mail-quote-container', '1')

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
        if el.getparent() is not None and (el.getparent().get('data-o-mail-quote') or el.getparent().get('data-o-mail-quote-container')) and not el.getparent().get('data-o-mail-quote-node'):
            el.set('data-o-mail-quote', '1')

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

    def allow_element(self, el):
        if el.tag == 'object' and el.get('type') == "image/svg+xml":
            return True
        return super(_Cleaner, self).allow_element(el)


def html_sanitize(src, silent=True, sanitize_tags=True, sanitize_attributes=False, sanitize_style=False, strip_style=False, strip_classes=False):
    if not src:
        return src
    src = ustr(src, errors='replace')
    # html: remove encoding attribute inside tags
    doctype = re.compile(r'(<[^>]*\s)(encoding=(["\'][^"\']*?["\']|[^\s\n\r>]+)(\s[^>]*|/)?>)', re.IGNORECASE | re.DOTALL)
    src = doctype.sub(u"", src)

    logger = logging.getLogger(__name__ + '.html_sanitize')

    # html encode email tags
    part = re.compile(r"(<(([^a<>]|a[^<>\s])[^<>]*)@[^<>]+>)", re.IGNORECASE | re.DOTALL)
    # remove results containing cite="mid:email_like@address" (ex: blockquote cite)
    # cite_except = re.compile(r"^((?!cite[\s]*=['\"]).)*$", re.IGNORECASE)
    src = part.sub(lambda m: (u'cite=' not in m.group(1) and u'alt=' not in m.group(1)) and misc.html_escape(m.group(1)) or m.group(1), src)
    # html encode mako tags <% ... %> to decode them later and keep them alive, otherwise they are stripped by the cleaner
    src = src.replace(u'<%', misc.html_escape(u'<%'))
    src = src.replace(u'%>', misc.html_escape(u'%>'))

    kwargs = {
        'page_structure': True,
        'style': strip_style,              # True = remove style tags/attrs
        'sanitize_style': sanitize_style,  # True = sanitize styling
        'forms': True,                     # True = remove form tags
        'remove_unknown_tags': False,
        'comments': False,
        'processing_instructions': False
    }
    if sanitize_tags:
        kwargs['allow_tags'] = allowed_tags
        if etree.LXML_VERSION >= (2, 3, 1):
            # kill_tags attribute has been added in version 2.3.1
            kwargs.update({
                'kill_tags': tags_to_kill,
                'remove_tags': tags_to_remove,
            })
        else:
            kwargs['remove_tags'] = tags_to_kill + tags_to_remove

    if sanitize_attributes and etree.LXML_VERSION >= (3, 1, 0):  # lxml < 3.1.0 does not allow to specify safe_attrs. We keep all attributes in order to keep "style"
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

    try:
        # some corner cases make the parser crash (such as <SCRIPT/XSS SRC=\"http://ha.ckers.org/xss.js\"></SCRIPT> in test_mail)
        cleaner = _Cleaner(**kwargs)
        cleaned = cleaner.clean_html(src)
        assert isinstance(cleaned, pycompat.text_type)
        # MAKO compatibility: $, { and } inside quotes are escaped, preventing correct mako execution
        cleaned = cleaned.replace(u'%24', u'$')
        cleaned = cleaned.replace(u'%7B', u'{')
        cleaned = cleaned.replace(u'%7D', u'}')
        cleaned = cleaned.replace(u'%20', u' ')
        cleaned = cleaned.replace(u'%5B', u'[')
        cleaned = cleaned.replace(u'%5D', u']')
        cleaned = cleaned.replace(u'%7C', u'|')
        cleaned = cleaned.replace(u'&lt;%', u'<%')
        cleaned = cleaned.replace(u'%&gt;', u'%>')
        # html considerations so real html content match database value
        cleaned.replace(u'\xa0', u'&nbsp;')
    except etree.ParserError as e:
        if u'empty' in pycompat.text_type(e):
            return u""
        if not silent:
            raise
        logger.warning(u'ParserError obtained when sanitizing %r', src, exc_info=True)
        cleaned = u'<p>ParserError when sanitizing</p>'
    except Exception:
        if not silent:
            raise
        logger.warning(u'unknown error obtained when sanitizing %r', src, exc_info=True)
        cleaned = u'<p>Unknown error when sanitizing</p>'

    # this is ugly, but lxml/etree tostring want to put everything in a 'div' that breaks the editor -> remove that
    if cleaned.startswith(u'<div>') and cleaned.endswith(u'</div>'):
        cleaned = cleaned[5:-6]

    return cleaned

#----------------------------------------------------------
# HTML/Text management
#----------------------------------------------------------

def html_keep_url(text):
    """ Transform the url into clickable link with <a/> tag """
    idx = 0
    final = ''
    link_tags = re.compile(r"""(?<!["'])((ftp|http|https):\/\/(\w+:{0,1}\w*@)?([^\s<"']+)(:[0-9]+)?(\/|\/([^\s<"']))?)(?![^\s<"']*["']|[^\s<"']*</a>)""")
    for item in re.finditer(link_tags, text):
        final += text[idx:item.start()]
        final += '<a href="%s" target="_blank">%s</a>' % (item.group(0), item.group(0))
        idx = item.end()
    final += text[idx:]
    return final

def html2plaintext(html, body_id=None, encoding='utf-8'):
    """ From an HTML text, convert the HTML to plain text.
    If @param body_id is provided then this is the tag where the
    body (not necessarily <body>) starts.
    """
    ## (c) Fry-IT, www.fry-it.com, 2007
    ## <peter@fry-it.com>
    ## download here: http://www.peterbe.com/plog/html2plaintext

    html = ustr(html)

    if not html:
        return ''

    tree = etree.fromstring(html, parser=etree.HTMLParser())

    if body_id is not None:
        source = tree.xpath('//*[@id=%s]' % (body_id,))
    else:
        source = tree.xpath('//body')
    if len(source):
        tree = source[0]

    url_index = []
    i = 0
    for link in tree.findall('.//a'):
        url = link.get('href')
        if url:
            i += 1
            link.tag = 'span'
            link.text = '%s [%s]' % (link.text, i)
            url_index.append(url)

    html = ustr(etree.tostring(tree, encoding=encoding))
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
    html = re.sub('<br\s*/?>', '\n', html)
    html = re.sub('<.*?>', ' ', html)
    html = html.replace(' ' * 2, ' ')
    html = html.replace('&gt;', '>')
    html = html.replace('&lt;', '<')
    html = html.replace('&amp;', '&')

    # strip all lines
    html = '\n'.join([x.strip() for x in html.splitlines()])
    html = html.replace('\n' * 2, '\n')

    for i, url in enumerate(url_index):
        if i == 0:
            html += '\n\n'
        html += ustr('[%s] %s\n') % (i + 1, url)

    return html

def plaintext2html(text, container_tag=False):
    """ Convert plaintext into html. Content of the text is escaped to manage
        html entities, using misc.html_escape().
        - all \n,\r are replaced by <br />
        - enclose content into <p>
        - convert url into clickable link
        - 2 or more consecutive <br /> are considered as paragraph breaks

        :param string container_tag: container of the html; by default the
            content is embedded into a <div>
    """
    text = misc.html_escape(ustr(text))

    # 1. replace \n and \r
    text = text.replace('\n', '<br/>')
    text = text.replace('\r', '<br/>')

    # 2. clickable links
    text = html_keep_url(text)

    # 3-4: form paragraphs
    idx = 0
    final = '<p>'
    br_tags = re.compile(r'(([<]\s*[bB][rR]\s*\/?[>]\s*){2,})')
    for item in re.finditer(br_tags, text):
        final += text[idx:item.start()] + '</p><p>'
        idx = item.end()
    final += text[idx:] + '</p>'

    # 5. container
    if container_tag:
        final = '<%s>%s</%s>' % (container_tag, final, container_tag)
    return ustr(final)

def append_content_to_html(html, content, plaintext=True, preserve=False, container_tag=False):
    """ Append extra content at the end of an HTML snippet, trying
        to locate the end of the HTML document (</body>, </html>, or
        EOF), and converting the provided content in html unless ``plaintext``
        is False.
        Content conversion can be done in two ways:
        - wrapping it into a pre (preserve=True)
        - use plaintext2html (preserve=False, using container_tag to wrap the
            whole content)
        A side-effect of this method is to coerce all HTML tags to
        lowercase in ``html``, and strip enclosing <html> or <body> tags in
        content if ``plaintext`` is False.

        :param str html: html tagsoup (doesn't have to be XHTML)
        :param str content: extra content to append
        :param bool plaintext: whether content is plaintext and should
            be wrapped in a <pre/> tag.
        :param bool preserve: if content is plaintext, wrap it into a <pre>
            instead of converting it into html
    """
    html = ustr(html)
    if plaintext and preserve:
        content = u'\n<pre>%s</pre>\n' % ustr(content)
    elif plaintext:
        content = '\n%s\n' % plaintext2html(content, container_tag)
    else:
        content = re.sub(r'(?i)(</?(?:html|body|head|!\s*DOCTYPE)[^>]*>)', '', content)
        content = u'\n%s\n' % ustr(content)
    # Force all tags to lowercase
    html = re.sub(r'(</?)(\w+)([ >])',
        lambda m: '%s%s%s' % (m.group(1), m.group(2).lower(), m.group(3)), html)
    insert_location = html.find('</body>')
    if insert_location == -1:
        insert_location = html.find('</html>')
    if insert_location == -1:
        return '%s%s' % (html, content)
    return '%s%s%s' % (html[:insert_location], content, html[insert_location:])

#----------------------------------------------------------
# Emails
#----------------------------------------------------------

# matches any email in a body of text
email_re = re.compile(r"""([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63})""", re.VERBOSE)

# matches a string containing only one email
single_email_re = re.compile(r"""^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}$""", re.VERBOSE)

# update command in emails body
command_re = re.compile("^Set-([a-z]+) *: *(.+)$", re.I + re.UNICODE)

# Updated in 7.0 to match the model name as well
# Typical form of references is <timestamp-openerp-record_id-model_name@domain>
# group(1) = the record ID ; group(2) = the model (if any) ; group(3) = the domain
reference_re = re.compile("<.*-open(?:object|erp)-(\\d+)(?:-([\w.]+))?[^>]*@([^>]*)>", re.UNICODE)
discussion_re = re.compile("<.*-open(?:object|erp)-private[^>]*@([^>]*)>", re.UNICODE)

mail_header_msgid_re = re.compile('<[^<>]+>')


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

def email_send(email_from, email_to, subject, body, email_cc=None, email_bcc=None, reply_to=False,
               attachments=None, message_id=None, references=None, openobject_id=False, debug=False, subtype='plain', headers=None,
               smtp_server=None, smtp_port=None, ssl=False, smtp_user=None, smtp_password=None, cr=None, uid=None):
    """Low-level function for sending an email (deprecated).

    :deprecate: since OpenERP 6.1, please use ir.mail_server.send_email() instead.
    :param email_from: A string used to fill the `From` header, if falsy,
                       config['email_from'] is used instead.  Also used for
                       the `Reply-To` header if `reply_to` is not provided
    :param email_to: a sequence of addresses to send the mail to.
    """

    # If not cr, get cr from current thread database
    local_cr = None
    if not cr:
        db_name = getattr(threading.currentThread(), 'dbname', None)
        if db_name:
            local_cr = cr = odoo.registry(db_name).cursor()
        else:
            raise Exception("No database cursor found, please pass one explicitly")

    # Send Email
    try:
        mail_server_pool = odoo.registry(cr.dbname)['ir.mail_server']
        res = False
        # Pack Message into MIME Object
        email_msg = mail_server_pool.build_email(email_from, email_to, subject, body, email_cc, email_bcc, reply_to,
                   attachments, message_id, references, openobject_id, subtype, headers=headers)

        res = mail_server_pool.send_email(cr, uid or 1, email_msg, mail_server_id=None,
                       smtp_server=smtp_server, smtp_port=smtp_port, smtp_user=smtp_user, smtp_password=smtp_password,
                       smtp_encryption=('ssl' if ssl else None), smtp_debug=debug)
    except Exception:
        _logger.exception("tools.email_send failed to deliver email")
        return False
    finally:
        if local_cr:
            cr.close()
    return res

def email_split(text):
    """ Return a list of the email addresses found in ``text`` """
    if not text:
        return []
    return [addr[1] for addr in getaddresses([text])
                # getaddresses() returns '' when email parsing fails, and
                # sometimes returns emails without at least '@'. The '@'
                # is strictly required in RFC2822's `addr-spec`.
                if addr[1]
                if '@' in addr[1]]

def email_split_and_format(text):
    """ Return a list of email addresses found in ``text``, formatted using
    formataddr. """
    if not text:
        return []
    return [formataddr((addr[0], addr[1])) for addr in getaddresses([text])
                # getaddresses() returns '' when email parsing fails, and
                # sometimes returns emails without at least '@'. The '@'
                # is strictly required in RFC2822's `addr-spec`.
                if addr[1]
                if '@' in addr[1]]

def email_references(references):
    ref_match, model, thread_id, hostname, is_private = False, False, False, False, False
    if references:
        ref_match = reference_re.search(references)
    if ref_match:
        model = ref_match.group(2)
        thread_id = int(ref_match.group(1))
        hostname = ref_match.group(3)
    else:
        ref_match = discussion_re.search(references)
        if ref_match:
            is_private = True
    return (ref_match, model, thread_id, hostname, is_private)

# was mail_message.decode()
def decode_smtp_header(smtp_header):
    """Returns unicode() string conversion of the given encoded smtp header
    text. email.header decode_header method return a decoded string and its
    charset for each decoded par of the header. This method unicodes the
    decoded header and join them in a complete string. """
    if isinstance(smtp_header, Header):
        smtp_header = ustr(smtp_header)
    if smtp_header:
        text = decode_header(smtp_header.replace('\r', ''))
        # The joining space will not be needed as of Python 3.3
        # See https://github.com/python/cpython/commit/07ea53cb218812404cdbde820647ce6e4b2d0f8e
        sep = ' ' if pycompat.PY2 else ''
        return sep.join([ustr(x[0], x[1]) for x in text])
    return u''

# was mail_thread.decode_header()
def decode_message_header(message, header, separator=' '):
    return separator.join(decode_smtp_header(h) for h in message.get_all(header, []) if h)
