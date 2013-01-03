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
import openerp.pooler as pooler
import random
import re
import socket
import threading
import time

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
    part = re.compile(r"(<[^<>]+@[^<>]+>)", re.IGNORECASE | re.DOTALL)
    src = part.sub(lambda m: cgi.escape(m.group(1)), src)
    
    # some corner cases make the parser crash (such as <SCRIPT/XSS SRC=\"http://ha.ckers.org/xss.js\"></SCRIPT> in test_mail)
    try:
        cleaner = clean.Cleaner(page_structure=True, style=False, safe_attrs_only=False, forms=False, kill_tags=tags_to_kill, remove_tags=tags_to_remove)
        cleaned = cleaner.clean_html(src)
    except TypeError, e:
        # lxml.clean version < 2.3.1 does not have a kill_tags attribute
        # to remove in 2014
        cleaner = clean.Cleaner(page_structure=True, style=False, safe_attrs_only=False, forms=False, remove_tags=tags_to_kill+tags_to_remove)
        cleaned = cleaner.clean_html(src)
    except:
        _logger.warning('html_sanitize failed to parse %s' % (src))
        cleaned = '<p>Impossible to parse</p>'
    return cleaned


#----------------------------------------------------------
# HTML Cleaner
#----------------------------------------------------------

def html_email_clean(html):
    """ html_email_clean: clean the html to display in the web client.
        - strip email quotes (remove blockquote nodes)
        - strip signatures (remove --\n{\n)Blahblah), by replacing <br> by
            \n to avoid ignoring signatures converted into html

        :param string html: sanitized html; tags like html or head should not
            be present in the html string. This method therefore takes as input
            html code coming from a sanitized source, like fields.html.
    """
    def _replace_matching_regex(regex, source, replace=''):
        dest = ''
        idx = 0
        for item in re.finditer(regex, source):
            dest += source[idx:item.start()] + replace
            idx = item.end()
        dest += source[idx:]
        return dest

    if not html or not isinstance(html, basestring):
        return html

    html = ustr(html)

    # 0. remove encoding attribute inside tags
    doctype = re.compile(r'(<[^>]*\s)(encoding=(["\'][^"\']*?["\']|[^\s\n\r>]+)(\s[^>]*|/)?>)', re.IGNORECASE | re.DOTALL)
    html = doctype.sub(r"", html)

    # 1. <br[ /]> -> \n, because otherwise the tree is obfuscated
    br_tags = re.compile(r'([<]\s*[bB][rR]\s*\/?[>])')
    html = _replace_matching_regex(br_tags, html, '__BR_TAG__')

    # 2. form a tree, handle (currently ?) pure-text by enclosing them in a pre
    root = lxml.html.fromstring(html)
    if not len(root) and root.text is None and root.tail is None:
        html = '<div>%s</div>' % html
        root = lxml.html.fromstring(html)

    # 2.5 remove quoted text in nodes
    quote_tags = re.compile(r'(\n(>)+[^\n\r]*)')
    for node in root.getiterator():
        if not node.text:
            continue
        node.text = _replace_matching_regex(quote_tags, node.text)

    # 3. remove blockquotes
    quotes = [el for el in root.getiterator(tag='blockquote')]
    for node in quotes:
        # copy the node tail into parent text
        if node.tail:
            parent = node.getparent()
            parent.text = parent.text or '' + node.tail
        # remove the node
        node.getparent().remove(node)

    # 4. strip signatures
    signature = re.compile(r'([-]{2}[\s]?[\r\n]{1,2}[^\z]+)')
    for elem in root.getiterator():
        if elem.text:
            match = re.search(signature, elem.text)
            if match:
                elem.text = elem.text[:match.start()] + elem.text[match.end():]
        if elem.tail:
            match = re.search(signature, elem.tail)
            if match:
                elem.tail = elem.tail[:match.start()] + elem.tail[match.end():]

    # 5. \n back to <br/>
    html = etree.tostring(root, pretty_print=True)
    html = html.replace('__BR_TAG__', '<br />')

    # 6. Misc cleaning :
    # - ClEditor seems to love using <div><br /><div> -> replace with <br />
    br_div_tags = re.compile(r'(<div>\s*<br\s*\/>\s*<\/div>)')
    html = _replace_matching_regex(br_div_tags, html, '<br />')

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

email_re = re.compile(r"""
    ([a-zA-Z][\w\.-]*[a-zA-Z0-9]     # username part
    @                                # mandatory @ sign
    [a-zA-Z0-9][\w\.-]*              # domain must start with a letter ... Ged> why do we include a 0-9 then?
     \.
     [a-z]{2,3}                      # TLD
    )
    """, re.VERBOSE)
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
            local_cr = cr = pooler.get_db(db_name).cursor()
        else:
            raise Exception("No database cursor found, please pass one explicitly")

    # Send Email
    try:
        mail_server_pool = pooler.get_pool(cr.dbname).get('ir.mail_server')
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
