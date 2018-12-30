# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
import cgi
import logging
import lxml.html
import lxml.html.clean as clean
import random
import re
import socket
import threading
import time
from email.utils import getaddresses, formataddr

import openerp
from openerp.loglevels import ustr
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# HTML Sanitizer
#----------------------------------------------------------

tags_to_kill = ["script", "head", "meta", "title", "link", "style", "frame", "iframe", "base", "object", "embed"]
tags_to_remove = ['html', 'body']
whitelist_classes = set(['WordSection1', 'MsoNormal', 'SkyDrivePlaceholder', 'oe_mail_expand', 'stopSpelling'])

# allow new semantic HTML5 tags
allowed_tags = clean.defs.tags | frozenset('article section header footer hgroup nav aside figure main'.split() + [etree.Comment])
safe_attrs = clean.defs.safe_attrs | frozenset(
    ['style',
     'data-oe-model', 'data-oe-id', 'data-oe-field', 'data-oe-type', 'data-oe-expression', 'data-oe-translation-id', 'data-oe-nodeid',
     'data-publish', 'data-id', 'data-res_id', 'data-member_id', 'data-view-id'
     ])


class _Cleaner(clean.Cleaner):
    def allow_element(self, el):
        if el.tag == 'object' and el.get('type') == "image/svg+xml":
            return True
        return super(_Cleaner, self).allow_element(el)

def html_sanitize(src, silent=True, strict=False, strip_style=False, strip_classes=False):
    if not src:
        return src
    src = ustr(src, errors='replace')

    logger = logging.getLogger(__name__ + '.html_sanitize')

    # html encode email tags
    part = re.compile(r"(<(([^a<>]|a[^<>\s])[^<>]*)@[^<>]+>)", re.IGNORECASE | re.DOTALL)
    # remove results containing cite="mid:email_like@address" (ex: blockquote cite)
    # cite_except = re.compile(r"^((?!cite[\s]*=['\"]).)*$", re.IGNORECASE)
    src = part.sub(lambda m: 'cite=' not in m.group(1) and cgi.escape(m.group(1)) or m.group(1), src)
    # html encode mako tags <% ... %> to decode them later and keep them alive, otherwise they are stripped by the cleaner
    src = src.replace('<%', cgi.escape('<%'))
    src = src.replace('%>', cgi.escape('%>'))

    kwargs = {
        'page_structure': True,
        'style': strip_style,       # True = remove style tags/attrs
        'forms': True,              # remove form tags
        'remove_unknown_tags': False,
        'allow_tags': allowed_tags,
        'comments': False,
        'processing_instructions': False
    }
    if etree.LXML_VERSION >= (2, 3, 1):
        # kill_tags attribute has been added in version 2.3.1
        kwargs.update({
            'kill_tags': tags_to_kill,
            'remove_tags': tags_to_remove,
        })
    else:
        kwargs['remove_tags'] = tags_to_kill + tags_to_remove

    if strict:
        if etree.LXML_VERSION >= (3, 1, 0):
            # lxml < 3.1.0 does not allow to specify safe_attrs. We keep all attributes in order to keep "style"
            if strip_classes:
                current_safe_attrs = safe_attrs - frozenset(['class'])
            else:
                current_safe_attrs = safe_attrs
            kwargs.update({
                'safe_attrs_only': True,
                'safe_attrs': current_safe_attrs,
            })
    else:
        kwargs['safe_attrs_only'] = False    # keep oe-data attributes + style
        kwargs['frames'] = False,            # do not remove frames (embbed video in CMS blogs)

    try:
        # some corner cases make the parser crash (such as <SCRIPT/XSS SRC=\"http://ha.ckers.org/xss.js\"></SCRIPT> in test_mail)
        cleaner = _Cleaner(**kwargs)
        cleaned = cleaner.clean_html(src)
        # MAKO compatibility: $, { and } inside quotes are escaped, preventing correct mako execution
        cleaned = cleaned.replace('%24', '$')
        cleaned = cleaned.replace('%7B', '{')
        cleaned = cleaned.replace('%7D', '}')
        cleaned = cleaned.replace('%20', ' ')
        cleaned = cleaned.replace('%5B', '[')
        cleaned = cleaned.replace('%5D', ']')
        cleaned = cleaned.replace('&lt;%', '<%')
        cleaned = cleaned.replace('%&gt;', '%>')
    except etree.ParserError, e:
        if 'empty' in str(e):
            return ""
        if not silent:
            raise
        logger.warning('ParserError obtained when sanitizing %r', src, exc_info=True)
        cleaned = '<p>ParserError when sanitizing</p>'
    except Exception:
        if not silent:
            raise
        logger.warning('unknown error obtained when sanitizing %r', src, exc_info=True)
        cleaned = '<p>Unknown error when sanitizing</p>'

    # this is ugly, but lxml/etree tostring want to put everything in a 'div' that breaks the editor -> remove that
    if cleaned.startswith('<div>') and cleaned.endswith('</div>'):
        cleaned = cleaned[5:-6]

    return cleaned


#----------------------------------------------------------
# HTML Cleaner
#----------------------------------------------------------

def html_email_clean(html, remove=False, shorten=False, max_length=300, expand_options=None,
                     protect_sections=False):
    """ html_email_clean: clean the html by doing the following steps:

     - try to strip email quotes, by removing blockquotes or having some client-
       specific heuristics
     - try to strip signatures
     - shorten the html to a maximum number of characters if requested

    Some specific use case:

     - MsOffice: ``div.style = border-top:solid;`` delimitates the beginning of
       a quote; detecting by finding WordSection1 of MsoNormal
     - Hotmail: ``hr.stopSpelling`` delimitates the beginning of a quote; detect
       Hotmail by funding ``SkyDrivePlaceholder``

    :param string html: sanitized html; tags like html or head should not
                        be present in the html string. This method therefore
                        takes as input html code coming from a sanitized source,
                        like fields.html.
    :param boolean remove: remove the html code that is unwanted; otherwise it
                           is only flagged and tagged
    :param boolean shorten: shorten the html; every excessing content will
                            be flagged as to remove
    :param int max_length: if shortening, maximum number of characters before
                           shortening
    :param dict expand_options: options for the read more link when shortening
                                the content.The used keys are the following:

                                 - oe_expand_container_tag: class applied to the
                                   container of the whole read more link
                                 - oe_expand_container_class: class applied to the
                                   link container (default: oe_mail_expand)
                                 - oe_expand_container_content: content of the
                                   container (default: ...)
                                 - oe_expand_separator_node: optional separator, like
                                   adding ... <br /><br /> <a ...>read more</a> (default: void)
                                 - oe_expand_a_href: href of the read more link itself
                                   (default: #)
                                 - oe_expand_a_class: class applied to the <a> containing
                                   the link itself (default: oe_mail_expand)
                                 - oe_expand_a_content: content of the <a> (default: read more)

                                The formatted read more link is the following:
                                <cont_tag class="oe_expand_container_class">
                                    oe_expand_container_content
                                    if expand_options.get('oe_expand_separator_node'):
                                        <oe_expand_separator_node/>
                                    <a href="oe_expand_a_href" class="oe_expand_a_class">
                                        oe_expand_a_content
                                    </a>
                                </span>
    """
    def _replace_matching_regex(regex, source, replace=''):
        """ Replace all matching expressions in source by replace """
        if not source:
            return source
        dest = ''
        idx = 0
        for item in re.finditer(regex, source):
            dest += source[idx:item.start()] + replace
            idx = item.end()
        dest += source[idx:]
        return dest

    def _create_node(tag, text, tail=None, attrs={}):
        new_node = etree.Element(tag)
        new_node.text = text
        new_node.tail = tail
        for key, val in attrs.iteritems():
            new_node.set(key, val)
        return new_node

    def _insert_new_node(node, index, new_node_tag, new_node_text, new_node_tail=None, new_node_attrs={}):
        new_node = _create_node(new_node_tag, new_node_text, new_node_tail, new_node_attrs)
        node.insert(index, new_node)
        return new_node

    def _tag_matching_regex_in_text(regex, node, new_node_tag='span', new_node_attrs={}):
        text = node.text or ''
        if not re.search(regex, text):
            return

        cur_node = node
        node.text = ''
        idx, iteration = 0, 0
        for item in re.finditer(regex, text):
            if iteration == 0:
                cur_node.text = text[idx:item.start()]
            else:
                _insert_new_node(node, (iteration - 1) * 2 + 1, new_node_tag, text[idx:item.start()])
            new_node = _insert_new_node(node, iteration * 2, new_node_tag, text[item.start():item.end()], None, new_node_attrs)

            cur_node = new_node
            idx = item.end()
            iteration += 1
        new_node = _insert_new_node(node, -1, new_node_tag, text[idx:] + (cur_node.tail or ''), None, {})

    def _truncate_node(node, position, simplify_whitespaces=True):
        """ Truncate a node text at a given position. This algorithm will shorten
        at the end of the word whose ending character exceeds position.

            :param bool simplify_whitespaces: whether to try to count all successive
                                              whitespaces as one character. This
                                              option should not be True when trying
                                              to keep 'pre' consistency.
        """
        if node.text is None:
            node.text = ''

        truncate_idx = -1
        if simplify_whitespaces:
            cur_char_nbr = 0
            word = None
            node_words = node.text.strip(' \t\r\n').split()
            for word in node_words:
                cur_char_nbr += len(word)
                if cur_char_nbr >= position:
                    break
            if word:
                truncate_idx = node.text.find(word) + len(word)
        else:
            truncate_idx = position
        if truncate_idx == -1 or truncate_idx > len(node.text):
            truncate_idx = len(node.text)

        # compose new text bits
        innertext = node.text[0:truncate_idx]
        outertext = node.text[truncate_idx:]
        node.text = innertext

        # create <span> ... <a href="#">read more</a></span> node
        read_more_node = _create_node(
            expand_options.get('oe_expand_container_tag', 'span'),
            expand_options.get('oe_expand_container_content', ' ... '),
            None,
            {'class': expand_options.get('oe_expand_container_class', 'oe_mail_expand')}
        )
        if expand_options.get('oe_expand_separator_node'):
            read_more_separator_node = _create_node(
                expand_options.get('oe_expand_separator_node'),
                '',
                None,
                {}
            )
            read_more_node.append(read_more_separator_node)
        read_more_link_node = _create_node(
            'a',
            expand_options.get('oe_expand_a_content', _('read more')),
            None,
            {
                'href': expand_options.get('oe_expand_a_href', '#'),
                'class': expand_options.get('oe_expand_a_class', 'oe_mail_expand'),
            }
        )
        read_more_node.append(read_more_link_node)
        # create outertext node
        overtext_node = _create_node('span', outertext)
        # tag node
        overtext_node.set('in_overlength', '1')
        # add newly created nodes in dom
        node.append(read_more_node)
        node.append(overtext_node)

    if expand_options is None:
        expand_options = {}
    whitelist_classes_local = whitelist_classes.copy()
    if expand_options.get('oe_expand_container_class'):
        whitelist_classes_local.add(expand_options.get('oe_expand_container_class'))
    if expand_options.get('oe_expand_a_class'):
        whitelist_classes_local.add(expand_options.get('oe_expand_a_class'))

    if not html or not isinstance(html, basestring):
        return html
    html = ustr(html)

    # Pre processing
    # ------------------------------------------------------------
    # TDE TODO: --- MAIL ORIGINAL ---: '[\-]{4,}([^\-]*)[\-]{4,}'

    # html: remove encoding attribute inside tags
    doctype = re.compile(r'(<[^>]*\s)(encoding=(["\'][^"\']*?["\']|[^\s\n\r>]+)(\s[^>]*|/)?>)', re.IGNORECASE | re.DOTALL)
    html = doctype.sub(r"", html)

    # html: ClEditor seems to love using <div><br /><div> -> replace with <br />
    br_div_tags = re.compile(r'(<div>\s*<br\s*\/>\s*<\/div>)', re.IGNORECASE)
    inner_html = _replace_matching_regex(br_div_tags, html, '<br />')

    # form a tree
    root = lxml.html.fromstring(inner_html)
    if not len(root) and root.text is None and root.tail is None:
        inner_html = '<div>%s</div>' % inner_html
        root = lxml.html.fromstring(inner_html)

    quote_tags = re.compile(r'(\n(>)+[^\n\r]*)')
    signature = re.compile(r'(^[-]{2,}[\s]?[\r\n]{1,2}[\s\S]+)', re.M)
    for node in root.iter():
        # remove all tails and replace them by a span element, because managing text and tails can be a pain in the ass
        if node.tail:
            tail_node = _create_node('span', node.tail)
            node.tail = None
            node.addnext(tail_node)

        # form node and tag text-based quotes and signature
        _tag_matching_regex_in_text(quote_tags, node, 'span', {'text_quote': '1'})
        _tag_matching_regex_in_text(signature, node, 'span', {'text_signature': '1'})

    # Processing
    # ------------------------------------------------------------

    # tree: tag nodes
    # signature_begin = False  # try dynamic signature recognition
    quoted = False
    quote_begin = False
    overlength = False
    replace_class = False
    overlength_section_id = None
    overlength_section_count = 0
    cur_char_nbr = 0
    for node in root.iter():
        # comments do not need processing
        # note: bug in node.get(value, default) for HtmlComments, default never returned
        if node.tag == etree.Comment:
            continue
        # do not take into account multiple spaces that are displayed as max 1 space in html
        node_text = ' '.join((node.text and node.text.strip(' \t\r\n') or '').split())

        # remove unwanted classes from node
        if node.get('class'):
            sanitize_classes = []
            for _class in node.get('class').split(' '):
                if _class in whitelist_classes_local:
                    sanitize_classes.append(_class)
                else:
                    sanitize_classes.append('cleaned_'+_class)
                    replace_class = True
            node.set('class', ' '.join(sanitize_classes))

        # root: try to tag the client used to write the html
        if 'WordSection1' in node.get('class', '') or 'MsoNormal' in node.get('class', ''):
            root.set('msoffice', '1')
        if 'SkyDrivePlaceholder' in node.get('class', '') or 'SkyDrivePlaceholder' in node.get('id', ''):
            root.set('hotmail', '1')

        # protect sections by tagging section limits and blocks contained inside sections, using an increasing id to re-find them later
        if node.tag == 'section':
            overlength_section_count += 1
            node.set('section_closure', str(overlength_section_count))
        if node.getparent() is not None and (node.getparent().get('section_closure') or node.getparent().get('section_inner')):
            node.set('section_inner', str(overlength_section_count))

        # state of the parsing: flag quotes and tails to remove
        if quote_begin:
            node.set('in_quote', '1')
            node.set('tail_remove', '1')
        # state of the parsing: flag when being in over-length content, depending on section content if defined (only when having protect_sections)
        if overlength:
            if not overlength_section_id or int(node.get('section_inner', overlength_section_count + 1)) > overlength_section_count:
                node.set('in_overlength', '1')
                node.set('tail_remove', '1')

        # find quote in msoffice / hotmail / blockquote / text quote and signatures
        if root.get('msoffice') and node.tag == 'div' and 'border-top:solid' in node.get('style', ''):
            quote_begin = True
            node.set('in_quote', '1')
            node.set('tail_remove', '1')
        if root.get('hotmail') and node.tag == 'hr' and ('stopSpelling' in node.get('class', '') or 'stopSpelling' in node.get('id', '')):
            quote_begin = True
            node.set('in_quote', '1')
            node.set('tail_remove', '1')
        if node.tag == 'blockquote' or node.get('text_quote') or node.get('text_signature'):
            # here no quote_begin because we want to be able to remove some quoted
            # text without removing all the remaining context
            quoted = True
            node.set('in_quote', '1')
        if node.getparent() is not None and node.getparent().get('in_quote'):
            # inside a block of removed text but not in quote_begin (see above)
            quoted = True
            node.set('in_quote', '1')

        # shorten:
        # if protect section:
        #   1/ find the first parent not being inside a section
        #   2/ add the read more link
        # else:
        #   1/ truncate the text at the next available space
        #   2/ create a 'read more' node, next to current node
        #   3/ add the truncated text in a new node, next to 'read more' node
        node_text = (node.text or '').strip().strip('\n').strip()
        if shorten and not overlength and cur_char_nbr + len(node_text) > max_length:
            node_to_truncate = node
            while node_to_truncate.getparent() is not None:
                if node_to_truncate.get('in_quote'):
                    node_to_truncate = node_to_truncate.getparent()
                elif protect_sections and (node_to_truncate.getparent().get('section_inner') or node_to_truncate.getparent().get('section_closure')):
                    node_to_truncate = node_to_truncate.getparent()
                    overlength_section_id = node_to_truncate.get('section_closure')
                else:
                    break

            overlength = True
            node_to_truncate.set('truncate', '1')
            if node_to_truncate == node:
                node_to_truncate.set('truncate_position', str(max_length - cur_char_nbr))
            else:
                node_to_truncate.set('truncate_position', str(len(node.text or '')))
        cur_char_nbr += len(node_text)

    # Tree modification
    # ------------------------------------------------------------

    for node in root.iter():
        if node.get('truncate'):
            _truncate_node(node, int(node.get('truncate_position', '0')), node.tag != 'pre')

    # Post processing
    # ------------------------------------------------------------

    to_remove = []
    for node in root.iter():
        if node.get('in_quote') or node.get('in_overlength'):
            # copy the node tail into parent text
            if node.tail and not node.get('tail_remove'):
                parent = node.getparent()
                parent.tail = node.tail + (parent.tail or '')
            to_remove.append(node)
        if node.get('tail_remove'):
            node.tail = ''
        # clean node
        for attribute_name in ['in_quote', 'tail_remove', 'in_overlength', 'msoffice', 'hotmail', 'truncate', 'truncate_position']:
            node.attrib.pop(attribute_name, None)
    for node in to_remove:
        if remove:
            node.getparent().remove(node)
        else:
            if not expand_options.get('oe_expand_a_class', 'oe_mail_expand') in node.get('class', ''):  # trick: read more link should be displayed even if it's in overlength
                node_class = node.get('class', '') + ' oe_mail_cleaned'
                node.set('class', node_class)

    if not overlength and not quote_begin and not quoted and not replace_class:
        return html

    # html: \n that were tail of elements have been encapsulated into <span> -> back to \n
    html = etree.tostring(root, pretty_print=False, encoding='UTF-8')
    linebreaks = re.compile(r'<span[^>]*>([\s]*[\r\n]+[\s]*)<\/span>', re.IGNORECASE | re.DOTALL)
    html = _replace_matching_regex(linebreaks, html, '\n')
    return ustr(html)


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
        html entities, using cgi.escape().
        - all \n,\r are replaced by <br />
        - enclose content into <p>
        - convert url into clickable link
        - 2 or more consecutive <br /> are considered as paragraph breaks

        :param string container_tag: container of the html; by default the
            content is embedded into a <div>
    """
    text = cgi.escape(ustr(text))

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
    html = re.sub(r'(</?)\W*(\w+)([ >])',
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

res_re = re.compile(r"\[([0-9]+)\]", re.UNICODE)
command_re = re.compile("^Set-([a-z]+) *: *(.+)$", re.I + re.UNICODE)

# Updated in 7.0 to match the model name as well
# Typical form of references is <timestamp-openerp-record_id-model_name@domain>
# group(1) = the record ID ; group(2) = the model (if any) ; group(3) = the domain
reference_re = re.compile("<.*-open(?:object|erp)-(\\d+)(?:-([\w.]+))?[^>]*@([^>]*)>", re.UNICODE)


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
    return "<%.15f.%s-openerp-%s@%s>" % (time.time(), rndstr, res_id, socket.gethostname())

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
            local_cr = cr = openerp.registry(db_name).cursor()
        else:
            raise Exception("No database cursor found, please pass one explicitly")

    # Send Email
    try:
        mail_server_pool = openerp.registry(cr.dbname)['ir.mail_server']
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
