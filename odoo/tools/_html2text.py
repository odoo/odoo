# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Modified html2text v.3.200.3 Aaron Swartz (me@aaronsw.com) under GNU GPL 3.
# Original version available on
# https://github.com/aaronsw/html2text/blob/master/html2text.py

# Apart from:
# * PEP8 styling and whitespace changes throughout the code, including renaming
#   functions and variables
# * add options to
#   * (not) use markdown newlines: double newlines and/or trailing spaces.
#   * (not) indent <pre> content
#   * ignore strike, bold, emphasis (split in two)
# * removing support for Google doc
# * removing support for non Python 3 code
# * removing options for having links per paragraph, skipping internal links
# * fixing typos,
# changes from the original version are preceded or suffixed by a [changes] or
# surrounded by [changes] and [/changes] comment tags.


# [changes] Simplify imports to python 3 only
from html import entities as html_entity_defs
import html.parser as html_parser
import re
import urllib.parse as urlparse
from textwrap import wrap
# [/changes]

# Use Unicode characters instead of their ascii pseudo-replacements
UNICODE_SNOB = 0

# Escape all special characters.  Output is less readable, but avoids corner case formatting issues.
ESCAPE_SNOB = False  # [change] 0 to False

# Wrap long lines at position. 0 for no wrapping.
BODY_WIDTH = 78

# [changes] additional constant values renamed and moved here
R_UNESCAPE = re.compile(r"&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));")
# [/changes]


# [changes] Move here from bottom, update name, signature, usage and docstring.
def _html2plaintext(html, markdown_newlines=False, markdown_pre=False, **kwargs):
    """
    :param markdown_newlines: Use double newlines and/or end lines with double space.
      Added as argument to avoid changing HTML2Text too much.
    :param kwargs: see HTML2Text docstring.
    """

    h = HTML2Text(markdown_newlines=markdown_newlines, indent_pre=markdown_pre, ** kwargs)
    return h.handle(html)


def name_to_codepoint(k):
    if k == 'apos':
        return ord("'")
    return html_entity_defs.name2codepoint[k]


unifiable = {'rsquo': "'", 'lsquo': "'", 'rdquo': '"', 'ldquo': '"',
             'copy': '(C)', 'mdash': '--', 'nbsp': ' ', 'rarr': '->', 'larr': '<-', 'middot': '*',
             'ndash': '-', 'oelig': 'oe', 'aelig': 'ae',
             'agrave': 'a', 'aacute': 'a', 'acirc': 'a', 'atilde': 'a', 'auml': 'a', 'aring': 'a',
             'egrave': 'e', 'eacute': 'e', 'ecirc': 'e', 'euml': 'e',
             'igrave': 'i', 'iacute': 'i', 'icirc': 'i', 'iuml': 'i',
             'ograve': 'o', 'oacute': 'o', 'ocirc': 'o', 'otilde': 'o', 'ouml': 'o',
             'ugrave': 'u', 'uacute': 'u', 'ucirc': 'u', 'uuml': 'u',
             'lrm': '', 'rlm': ''}

# [Changes] simplification with Py3 [/changes]
unifiable_n = {name_to_codepoint(k): v for k, v in unifiable.items()}


def only_white(line):
    """Return true if the line does only consist of whitespace characters."""
    for c in line:
        if c != ' ' and c != '  ':
            return c == ' '
    return line


def hn(tag):
    if tag[0] == 'h' and len(tag) == 2:
        try:
            n = int(tag[1])
            if n in range(1, 10):
                return n
        except ValueError:
            return 0


def css_rules_to_dict(style):
    """
    :param str style: css ruleset
    :rtype: dict
    """
    return dict(map(str.strip, rule.split(':', 1)) for rule in style.split(';') if ':' in rule)  # [changes] use map


def dumb_css_parser(data):
    """returns a hash of css selectors, each of which contains a hash of css attributes"""
    # remove @import sentences
    data += ';'
    import_index = data.find('@import')
    while import_index != -1:
        data = data[0:import_index] + data[data.find(';', import_index) + 1:]
        import_index = data.find('@import')

    # parse the css. reverted from dictionary compehension in order to support older pythons
    elements = [x.split('{') for x in data.split('}') if '{' in x.strip()]
    try:
        elements = dict([(a.strip(), css_rules_to_dict(b)) for a, b in elements])
    except ValueError:
        elements = {}  # not that important

    return elements


def element_style(attrs, style_def, parent_style):
    """returns a hash of the 'final' style attributes of the element"""
    style = parent_style.copy()
    if 'class' in attrs:
        for css_class in attrs['class'].split():
            css_style = style_def['.' + css_class]
            style.update(css_style)
    if 'style' in attrs:
        immediate_style = css_rules_to_dict(attrs['style'])
        style.update(immediate_style)
    return style


def list_numbering_start(attrs):
    """extract numbering from list element attributes"""
    if 'start' in attrs:
        return int(attrs['start']) - 1
    else:
        return 0


class HTML2Text(html_parser.HTMLParser):
    # [changes]: add config parameters
    def __init__(self, out=None, baseurl='', ignore_bold=False, ignore_emphasis=True,
                 ignore_images=True, ignore_links=False, ignore_strike=True, indent_pre=True,
                 inline_links=False, markdown_newlines=True):
        """
        :param out:
        :param baseurl:
        :param ignore_images: Do not include images in output
        :param ignore_links:
        :param ignore_bold: Ignore `b` and `strong` tags
        :param ignore_emphasis: Ignore `em`, `i`, and `u` tags
        :param ignore_strike: Ignore `del`, `strike`, and `s` tags
        :param indent_pre: Indent <pre> tags
        :param inline_links: Use inline, rather than reference, formatting for images and links
        :param markdown_newlines: Use double newlines and or double spaces at end of lines
        """
        html_parser.HTMLParser.__init__(self)

        # Config options
        self.unicode_snob = UNICODE_SNOB
        self.escape_snob = ESCAPE_SNOB
        # [changes]  Remove links_each_paragraph option
        self.body_width = BODY_WIDTH
        self.inline_links = inline_links
        self.ignore_bold = ignore_bold
        self.ignore_links = ignore_links
        self.ignore_images = ignore_images
        self.ignore_emphasis = ignore_emphasis
        self.ignore_strike = ignore_strike
        self.ul_item_mark = '*'
        self.emphasis_mark = '*'  # [change] was '_'
        self.strong_mark = '**'
        self.hr_markdown = "* * *"
        self.markdown_newlines = markdown_newlines
        self.pre_indent = "    " if indent_pre else ""

        if out is None:
            self.out = self.out_text_f
        else:
            self.out = out

        self.out_text_list = []  # empty list to store output characters before they are "joined"

        self.out_text = str()

        self.quiet = 0
        self.p_p = 0  # number of newline character to print before next output
        self.out_count = 0
        self.start = True
        self.space = 0
        self.a = []
        self.astack = []
        self.maybe_automatic_link = None
        self.absolute_url_matcher = re.compile(r'^[a-zA-Z+]+://')
        self.a_count = 0
        self.list = []
        self.blockquote = 0
        self.pre = 0
        self.start_pre = 0
        self.code = False
        self.br_toggle = ''
        self.lastWasNL = 0
        self.lastWasList = False
        self.style = 0
        self.style_def = {}
        self.tag_stack = []
        self.emphasis = 0
        self.drop_white_space = 0
        self.in_header = False
        self.abbr_title = None  # current abbreviation definition
        self.abbr_data = None  # last inner HTML (for abbr being defined)
        self.abbr_list = {}  # stack of abbreviations to write later
        self.baseurl = baseurl

        unifiable_n.pop(name_to_codepoint('nbsp'), None)
        unifiable['nbsp'] = '&nbsp_place_holder;'

    def feed(self, data):
        data = data.replace("</' + 'script>", "</ignore>")
        html_parser.HTMLParser.feed(self, data)

    def handle(self, data):
        self.feed(data)
        self.feed("")
        return self.optwrap(self.close())

    def out_text_f(self, s):
        self.out_text_list.append(s)
        if s:
            self.lastWasNL = s[-1] == '\n'

    def close(self):
        """:rtype: str"""  # # [changes] add rtype
        super().close()  # [changes] use super

        self.pbr()
        self.o('', False, 'end')

        self.out_text = self.out_text.join(self.out_text_list)
        if self.unicode_snob:
            nbsp = chr(name_to_codepoint('nbsp'))
        else:
            nbsp = u' '
        self.out_text = self.out_text.replace(u'&nbsp_place_holder;', nbsp)

        return self.out_text

    def handle_charref(self, c):
        self.o(self.charref(c), True)

    def handle_entityref(self, c):
        self.o(self.entityref(c), True)

    def handle_starttag(self, tag, attrs):
        self.handle_tag(tag, attrs, True)

    def handle_endtag(self, tag):
        self.handle_tag(tag, None, False)

    def previous_index(self, attrs):
        """ returns the index of certain set of attributes (of a link) in the
            self.a list
            If the set of attributes is not found, returns None
        """
        # [changes] `in` replaces of `has_key` + styling + "match" simplification
        if 'href' not in attrs:
            return None

        i = -1
        for a in self.a:
            i += 1

            if 'href' in a and a['href'] == attrs['href']:
                if 'title' not in a and 'title' not in attrs:
                    return i
                if 'title' in a and 'title' in attrs and a['title'] == attrs['title']:
                    return i
        # [/changes]

    def drop_last(self, nb_letters):
        if not self.quiet:
            self.out_text = self.out_text[:-nb_letters]

    def handle_tag(self, tag, attrs, start):
        if attrs is None:
            attrs = {}
        else:
            attrs = dict(attrs)

        if hn(tag):
            self.p()
            if start:
                self.in_header = True
                self.o(hn(tag) * "#" + ' ')
            else:
                self.in_header = False
                return  # prevent redundant emphasis marks on headers

        if tag in ['p', 'div']:
            self.p()
        # [changes] use elifs

        elif tag == "br" and start:
            self.o("  \n" if self.markdown_newlines else '\n')

        elif tag == "hr" and start:
            self.p()
            self.o(self.hr_markdown)
            self.p()

        elif tag in ["head", "style", 'script']:
            self.quiet += 1 if start else -1  # [change] use 'ternary' assignment

        elif tag == "style":
            self.style += 1 if start else -1  # [change] use 'ternary' assignment

        elif tag == "body":
            self.quiet = 0  # sites like 9rules.com never close <head>

        elif tag == "blockquote":
            if start:
                self.p()
                self.o('> ', pure_data=False, force=True)
                self.start = 1
                self.blockquote += 1
            else:
                self.blockquote -= 1
                self.p()

        elif tag in ['em', 'i', 'u'] and not self.ignore_emphasis:
            self.o(self.emphasis_mark)
        elif tag in ['strong', 'b'] and not self.ignore_bold:
            self.o(self.strong_mark)
        elif tag in ['del', 'strike', 's'] and not self.ignore_strike:
            if start:
                self.o("<" + tag + ">")
            else:
                self.o("</" + tag + ">")

        elif tag in ["code", "tt"] and not self.pre:
            self.o('`')  # TODO: `` `this` ``
        elif tag == "abbr":
            if start:
                self.abbr_title = None
                self.abbr_data = ''
                if 'title' in attrs:
                    self.abbr_title = attrs['title']
            else:
                if self.abbr_title is not None:
                    self.abbr_list[self.abbr_data] = self.abbr_title
                    self.abbr_title = None
                self.abbr_data = ''

        elif tag == "a" and not self.ignore_links:
            if start:
                if 'href' in attrs and not attrs['href'].startswith('#'):
                    self.astack.append(attrs)
                    self.maybe_automatic_link = attrs['href']
                else:
                    self.astack.append(None)
            else:
                if self.astack:
                    a = self.astack.pop()
                    if self.maybe_automatic_link:
                        self.maybe_automatic_link = None
                    elif a:
                        if self.inline_links:
                            self.o("](" + _escape_md(a['href']) + ")")
                        else:
                            i = self.previous_index(a)
                            if i is not None:
                                a = self.a[i]
                            else:
                                self.a_count += 1
                                a['count'] = self.a_count
                                a['out_count'] = self.out_count
                                self.a.append(a)
                            self.o("][" + str(a['count']) + "]")

        elif tag == "img" and start and not self.ignore_images:
            if 'src' in attrs:
                attrs['href'] = attrs['src']
                alt = attrs.get('alt', '')
                self.o("![" + _escape_md(alt) + "]")

                if self.inline_links:
                    self.o("(" + _escape_md(attrs['href']) + ")")
                else:
                    # [changes] call function [/changes]

                    i = self.previous_index(attrs)
                    if i is not None:
                        attrs = self.a[i]
                    else:
                        self.a_count += 1
                        attrs['count'] = self.a_count
                        attrs['out_count'] = self.out_count
                        self.a.append(attrs)
                    self.o("[" + str(attrs['count']) + "]")

        elif tag == 'dl' and start:
            self.p()
        elif tag == 'dt' and not start:
            self.pbr()
        elif tag == 'dd' and start:
            self.o('    ')
        elif tag == 'dd' and not start:
            self.pbr()

        elif tag in ["ol", "ul"]:
            # Google Docs create sub lists as top level lists  # odoo: kept as may be the case of any code
            if (not self.list) and (not self.lastWasList):
                self.p()
            if start:
                list_style = tag
                numbering_start = list_numbering_start(attrs)
                self.list.append({'name': list_style, 'num': numbering_start})
            else:
                if self.list:
                    self.list.pop()
            self.lastWasList = True
        else:
            self.lastWasList = False

        if tag == 'li':
            self.pbr()
            if start:
                if self.list:
                    li = self.list[-1]
                else:
                    li = {'name': 'ul', 'num': 0}
                nest_count = len(self.list)
                self.o("  " * nest_count)  # TODO: line up <ol><li>s > 9 correctly.
                if li['name'] == "ul":
                    self.o(self.ul_item_mark + " ")
                elif li['name'] == "ol":
                    li['num'] += 1
                    self.o(str(li['num']) + ". ")
                self.start = 1

        elif tag in ["table", "tr"] and start:
            self.p()
        elif tag == 'td':
            self.pbr()

        elif tag == "pre":
            if start:
                self.start_pre = 1
                self.pre = 1
            else:
                self.pre = 0
            self.p()

    def pbr(self):
        if self.p_p == 0:
            self.p_p = 1

    def p(self):
        self.p_p = 2 if self.markdown_newlines else 1

    def soft_br(self):
        self.pbr()
        self.br_toggle = '  ' if self.markdown_newlines else ''

    # [changes] flags to `bool` type
    def o(self, data, pure_data=False, force=False):
        """
        :param data:
        :param bool pure_data:
        :param bool|str force:
        """
        if self.abbr_data is not None:
            self.abbr_data += data

        if not self.quiet:
            if pure_data and not self.pre:
                data = re.sub(r'\s+', ' ', data)  # [changes] use of r string
                if data and data[0] == ' ':
                    self.space = 1
                    data = data[1:]
            if not data and not force:
                return

            if self.start_pre:
                # self.out(" :") #TODO: not output when already one there
                if not data.startswith("\n"):  # <pre>stuff...
                    data = "\n" + data

            bq = (">" * self.blockquote)
            if not (force and data and data[0] == ">") and self.blockquote:
                bq += " "

            if self.pre:
                if self.pre_indent:  # [changes] add self.pre_indent
                    if not self.list:
                        bq += self.pre_indent
                    # else: list content is already partially indented
                    bq += self.pre_indent * len(self.list)  # [changes] Simplification
                data = data.replace("\n", "\n" + bq)

            if self.start_pre:
                self.start_pre = 0
                if self.list:
                    data = data.lstrip("\n")  # use existing initial indentation

            if self.start:
                self.space = 0
                self.p_p = 0
                self.start = False

            if force == 'end':
                # It's the end.
                self.p_p = 0
                self.out("\n")
                self.space = 0

            if self.p_p:
                self.out((self.br_toggle + '\n' + bq) * self.p_p)
                self.space = 0
                self.br_toggle = ''

            if self.space:
                if not self.lastWasNL:
                    self.out(' ')
                self.space = 0

            if self.a and force == "end":  # [/changes] remove links_per_paragraph option
                self.out("\n")

                new_a = []
                for link in self.a:
                    if self.out_count > link['out_count']:
                        self.out("   [" + str(link['count']) + "]: " + urlparse.urljoin(self.baseurl, link['href']))
                        # [changes] `has_key` => `in`
                        if 'title' in link:
                            self.out(" (" + link['title'] + ")")
                        self.out("\n")
                    else:
                        new_a.append(link)

                if self.a != new_a:
                    self.out("\n")  # Don't need an extra line when nothing was done.

                self.a = new_a

            if self.abbr_list and force == "end":
                for abbr, definition in self.abbr_list.items():
                    self.out("  *[" + abbr + "]: " + definition + "\n")

            self.p_p = 0
            self.out(data)
            self.out_count += 1

    def handle_data(self, data):
        if r'\/script>' in data:
            self.quiet -= 1

        if self.style:
            self.style_def.update(dumb_css_parser(data))

        if self.maybe_automatic_link is not None:
            href = self.maybe_automatic_link
            if href == data and self.absolute_url_matcher.match(href):
                self.o("<" + data + ">")
                return
            else:
                self.o("[")
                self.maybe_automatic_link = None

        if not self.code and not self.pre:
            data = _escape_md_section(data, snob=self.escape_snob)
        self.o(data, True)

    def unknown_decl(self, data):
        pass

    def charref(self, name):
        if name[0] in ['x', 'X']:
            c = int(name[1:], 16)
        else:
            c = int(name)

        if not self.unicode_snob and c in unifiable_n.keys():
            return unifiable_n[c]

        return chr(c)

    def entityref(self, c):
        if not self.unicode_snob and c in unifiable.keys():
            return unifiable[c]
        try:
            return chr(name_to_codepoint(c))
        except KeyError:
            return "&" + c + ';'

    def replace_entities(self, s):
        s = s.group(1)
        if s[0] == "#":
            return self.charref(s[1:])
        else:
            return self.entityref(s)

    def unescape(self, s):
        return R_UNESCAPE.sub(self.replace_entities, s)

    def optwrap(self, text):
        """Wrap all paragraphs in the provided text."""
        if not self.body_width:
            return text

        result = ''
        newlines = 0
        for para in text.split("\n"):
            if len(para) > 0:
                if not skip_wrap(para, self.markdown_newlines):
                    result += "\n".join(wrap(para, self.body_width))
                    if para.endswith('  '):
                        result += "  \n"
                        newlines = 1
                    else:
                        result += "\n\n"
                        newlines = 2
                else:
                    if not only_white(para):
                        result += para + "\n"
                        newlines = 1
            else:
                if newlines < 2:
                    result += "\n"
                    newlines += 1
        return result


ordered_list_matcher = re.compile(r'\d+\.\s')
# [changes] remove redundant `\`
unordered_list_matcher = re.compile(r'[-*+]\s')
md_chars_matcher = re.compile(r"([\\\[\]()])")
md_chars_matcher_all = re.compile(r"([`*_{}\[\]()#!])")
# [/changes]
md_dot_matcher = re.compile(r"""
    ^             # start of line
    (\s*\d+)      # optional whitespace and a number
    (\.)          # dot
    (?=\s)        # lookahead assert whitespace
    """, re.MULTILINE | re.VERBOSE)
md_plus_matcher = re.compile(r"""
    ^
    (\s*)
    (\+)
    (?=\s)
    """, flags=re.MULTILINE | re.VERBOSE)
# [changes] remove dash escape [/changes]

slash_chars = r'\`*_{}[]()#+-.!'
md_backslash_matcher = re.compile(r'''
    (\\)          # match one slash
    (?=[%s])      # followed by a char that requires escaping
    ''' % re.escape(slash_chars),
                                  flags=re.VERBOSE)


def skip_wrap(para, markdown_newlines=True):
    if not markdown_newlines:  # [changes] this block is added
        return True
    # If the text begins with only two "--", possibly preceded by whitespace, that's
    # an emdash; so wrap.
    stripped = para.lstrip()
    if stripped[0:2] == "--" and len(stripped) > 2 and stripped[2] != "-":
        return False
    # I'm not sure what this is for; I thought it was to detect lists, but there's
    # a <br>-inside-<span> case in one of the tests that also depends upon it.
    if stripped[0:1] == '-' or stripped[0:1] == '*':
        return True
    # If the text begins with a single -, *, or +, followed by a space, or an integer,
    # followed by a ., followed by a space (in either case optionally preceeded by
    # whitespace), it's a list; don't wrap.
    if ordered_list_matcher.match(stripped) or unordered_list_matcher.match(stripped):
        return True
    return False


# [changes] remove unused commands [/changes]
def _escape_md(text):
    """Escapes markdown-sensitive characters within other markdown constructs."""
    return md_chars_matcher.sub(r"\\\1", text)


def _escape_md_section(text, snob=False):
    """Escapes markdown-sensitive characters across whole document sections."""
    text = md_backslash_matcher.sub(r"\\\1", text)
    if snob:
        text = md_chars_matcher_all.sub(r"\\\1", text)
    text = md_dot_matcher.sub(r"\1\\\2", text)
    text = md_plus_matcher.sub(r"\1\\\2", text)
    # [changes] Remove dash escape [/changes]
    return text
