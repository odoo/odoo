# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2012 OpenERP S.A. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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

import openerp
from openerp.loglevels import ustr

_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# HTML Sanitizer
#----------------------------------------------------------

tags_to_kill = ["script", "head", "meta", "title", "link", "style", "frame", "iframe", "base", "object", "embed"]
tags_to_remove = ['html', 'body', 'font']


def html_sanitize(src):
    if not src:
        return src
    src = ustr(src, errors='replace')

    # html encode email tags
    part = re.compile(r"(<(([^a<>]|a[^<>\s])[^<>]*)@[^<>]+>)", re.IGNORECASE | re.DOTALL)
    src = part.sub(lambda m: cgi.escape(m.group(1)), src)

    # some corner cases make the parser crash (such as <SCRIPT/XSS SRC=\"http://ha.ckers.org/xss.js\"></SCRIPT> in test_mail)
    try:
        cleaner = clean.Cleaner(page_structure=True, style=False, safe_attrs_only=False, forms=False, kill_tags=tags_to_kill, remove_tags=tags_to_remove)
        cleaned = cleaner.clean_html(src)
    except TypeError, e:
        # lxml.clean version < 2.3.1 does not have a kill_tags attribute
        # to remove in 2014
        cleaner = clean.Cleaner(page_structure=True, style=False, safe_attrs_only=False, forms=False, remove_tags=tags_to_kill + tags_to_remove)
        cleaned = cleaner.clean_html(src)
    except etree.ParserError, e:
        _logger.warning('html_sanitize: ParserError "%s" obtained when sanitizing "%s"' % (e, src))
        cleaned = '<p>ParserError when sanitizing</p>'
    except Exception, e:
        _logger.warning('html_sanitize: unknown error "%s" obtained when sanitizing "%s"' % (e, src))
        cleaned = '<p>Unknown error when sanitizing</p>'
    return cleaned


#----------------------------------------------------------
# HTML Cleaner
#----------------------------------------------------------

def html_email_clean(html, remove_unwanted=False, use_max_length=False, max_length=300):
    """ html_email_clean: clean the html to display in the web client.
        - strip email quotes (remove blockquote nodes)
        - strip signatures (remove --\n{\n)Blahblah), by replacing <br> by
            \n to avoid ignoring signatures converted into html

        :param string html: sanitized html; tags like html or head should not
            be present in the html string. This method therefore takes as input
            html code coming from a sanitized source, like fields.html.
    """
    def _replace_matching_regex(regex, source, replace=''):
        if not source:
            return source
        dest = ''
        idx = 0
        for item in re.finditer(regex, source):
            dest += source[idx:item.start()] + replace
            idx = item.end()
        dest += source[idx:]
        return dest

    def _tag_matching_regex_in_text(regex, node, new_node_tag='span', new_node_attrs=None):
        # print '\t_tag_matching_regex_in_text'
        text = node.text or ''
        node.text = ''
        cur_node = node
        idx = 0
        caca = 0
        for item in re.finditer(regex, text):
            # print '\t\tfound', item.start(), item.end(), '-', text[item.start():item.end()], '-'
            if caca == 0:
                cur_node.text = text[idx:item.start()]
            else:
                cur_node.tail = text[idx:item.start()]

            # create element
            new_node = etree.Element(new_node_tag)
            new_node.text = text[item.start():item.end()]
            for key, val in new_node_attrs.iteritems():
                new_node.set(key, val)

            # insert element in DOM
            node.insert(caca, new_node)
            cur_node = new_node
            idx = item.end()
            caca += 1
        if caca == 0:
            cur_node.text = (cur_node.text or '') + text[idx:]
        else:
            cur_node.tail = text[idx:] + (cur_node.tail or '')

    if not html or not isinstance(html, basestring):
        return html
    html = ustr(html)

    # Pre processing
    # ------------------------------------------------------------

    # --- MAIL ORIGINAL ---: '[\-]{4,}([^\-]*)[\-]{4,}'

    # html: remove encoding attribute inside tags
    doctype = re.compile(r'(<[^>]*\s)(encoding=(["\'][^"\']*?["\']|[^\s\n\r>]+)(\s[^>]*|/)?>)', re.IGNORECASE | re.DOTALL)
    html = doctype.sub(r"", html)

    # html: ClEditor seems to love using <div><br /><div> -> replace with <br />
    br_div_tags = re.compile(r'(<div>\s*<br\s*\/>\s*<\/div>)')
    html = _replace_matching_regex(br_div_tags, html, '<br />')

    # html: <br[ /]> -> \n, to de-obfuscate the tree
    br_tags = re.compile(r'([<]\s*[bB][rR]\s*\/?[>])')
    html = _replace_matching_regex(br_tags, html, '__BR_TAG__')

    # form a tree
    root = lxml.html.fromstring(html)
    if not len(root) and root.text is None and root.tail is None:
        html = '<div>%s</div>' % html
        root = lxml.html.fromstring(html)

    # form node and tag text-based quotes and signature
    quote_tags = re.compile(r'(\n(>)+[^\n\r]*)')
    signature = re.compile(r'([-]{2}[\s]?[\r\n]{1,2}[^\z]+)')
    for node in root.getiterator():
        _tag_matching_regex_in_text(quote_tags, node, 'span', {'text_quote': '1'})
        _tag_matching_regex_in_text(signature, node, 'span', {'text_signature': '1'})

    # Processing
    # ------------------------------------------------------------

    # tree: tag nodes
    quote_begin = False
    overlength = False
    cur_char_nbr = 0
    for node in root.getiterator():
        if node.get('class') in ['WordSection1', 'MsoNormal']:
            root.set('msoffice', '1')
        if node.get('class') in ['SkyDrivePlaceholder'] or node.get('id') in ['SkyDrivePlaceholder']:
            root.set('hotmail', '1')

        if quote_begin:
            node.set('quote', '1')
        if overlength:
            node.set('remove', '1')
            node.set('tail_remove', '1')

        if root.get('msoffice') and node.tag == 'div' and 'border-top:solid' in node.get('style', ''):
            quote_begin = True
        if root.get('hotmail') and node.tag == 'hr' and ('stopSpelling' in node.get('class', '') or 'stopSpelling' in node.get('id', '')):
            quote_begin = True

        if use_max_length:
            if not overlength and cur_char_nbr + len(node.text or '') > max_length:
                overlength = True
                node.text = node.text[0:(max_length - cur_char_nbr)] + ' <span class="oe_mail_expand"><a href="#">... read more</a></span>'
                node.set('tail_remove', '1')
            cur_char_nbr += len(node.text or '')

        if node.tag == 'blockquote' or node.get('text_quote') or node.get('text_signature'):
            node.set('remove', '1')
        if quote_begin:
            node.set('remove', '1')
            node.set('tail_remove', '1')

    # Post processing
    # ------------------------------------------------------------

    if remove_unwanted:
        to_delete = []
        for node in root.getiterator():
            if node.get('remove'):
                # copy the node tail into parent text
                if node.tail and not node.get('tail_remove'):
                    parent = node.getparent()
                    parent.tail = node.tail + (parent.tail or '')
                to_delete.append(node)
            if node.get('tail_remove'):
                node.tail = ''
        for node in to_delete:
            node.getparent().remove(node)

    # html: \n back to <br/>
    html = etree.tostring(root, pretty_print=True)
    html = html.replace('__BR_TAG__', '<br />')

    return html


#----------------------------------------------------------
# HTML/Text management
#----------------------------------------------------------

def html2plaintext(html, body_id=None, encoding='utf-8'):
    """ From an HTML text, convert the HTML to plain text.
    If @param body_id is provided then this is the tag where the
    body (not necessarily <body>) starts.
    """
    ## (c) Fry-IT, www.fry-it.com, 2007
    ## <peter@fry-it.com>
    ## download here: http://www.peterbe.com/plog/html2plaintext

    html = ustr(html)
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
        - 2 or more consecutive <br /> are considered as paragraph breaks

        :param string container_tag: container of the html; by default the
            content is embedded into a <div>
    """
    text = cgi.escape(ustr(text))

    # 1. replace \n and \r
    text = text.replace('\n', '<br/>')
    text = text.replace('\r', '<br/>')

    # 2-3: form paragraphs
    idx = 0
    final = '<p>'
    br_tags = re.compile(r'(([<]\s*[bB][rR]\s*\/?[>]\s*){2,})')
    for item in re.finditer(br_tags, text):
        final += text[idx:item.start()] + '</p><p>'
        idx = item.end()
    final += text[idx:] + '</p>'

    # 4. container
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
        content = re.sub(r'(?i)(</?html.*>|</?body.*>|<!\W*DOCTYPE.*>)', '', content)
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
email_re = re.compile(r"""([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6})""", re.VERBOSE) 

# matches a string containing only one email
single_email_re = re.compile(r"""^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$""", re.VERBOSE)

res_re = re.compile(r"\[([0-9]+)\]", re.UNICODE)
command_re = re.compile("^Set-([a-z]+) *: *(.+)$", re.I + re.UNICODE)

# Updated in 7.0 to match the model name as well
# Typical form of references is <timestamp-openerp-record_id-model_name@domain>
# group(1) = the record ID ; group(2) = the model (if any) ; group(3) = the domain
reference_re = re.compile("<.*-open(?:object|erp)-(\\d+)(?:-([\w.]+))?.*@(.*)>", re.UNICODE)

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
            local_cr = cr = openerp.registry(db_name).db.cursor()
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
    return re.findall(r'([^ ,<@]+@[^> ,]+)', text)
