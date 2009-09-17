# filters.py
# Copyright (C) 2006, 2007, 2008 Geoffrey T. Dairiki <dairiki@dairiki.org> and Michael Bayer <mike_mp@zzzcomputing.com>
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php


import re, cgi, urllib, htmlentitydefs, codecs
from StringIO import StringIO

xml_escapes = {
    '&' : '&amp;',
    '>' : '&gt;', 
    '<' : '&lt;', 
    '"' : '&#34;',   # also &quot; in html-only
    "'" : '&#39;'    # also &apos; in html-only    
}
# XXX: &quot; is valid in HTML and XML
#      &apos; is not valid HTML, but is valid XML

def html_escape(string):
    return cgi.escape(string, True)

def xml_escape(string):
    return re.sub(r'([&<"\'>])', lambda m: xml_escapes[m.group()], string)

def url_escape(string):
    # convert into a list of octets
    string = string.encode("utf8")
    return urllib.quote_plus(string)

def url_unescape(string):
    text = urllib.unquote_plus(string)
    if not is_ascii_str(text):
        text = text.decode("utf8")
    return text

def trim(string):
    return string.strip()


class Decode(object):
    def __getattr__(self, key):
        def decode(x):
            if isinstance(x, unicode):
                return x
            elif not isinstance(x, str):
                return unicode(str(x), encoding=key)
            else:
                return unicode(x, encoding=key)
        return decode
decode = Decode()
        
            
_ASCII_re = re.compile(r'\A[\x00-\x7f]*\Z')

def is_ascii_str(text):
    return isinstance(text, str) and _ASCII_re.match(text)

################################################################    

class XMLEntityEscaper(object):
    def __init__(self, codepoint2name, name2codepoint):
        self.codepoint2entity = dict([(c, u'&%s;' % n)
                                      for c,n in codepoint2name.iteritems()])
        self.name2codepoint = name2codepoint

    def escape_entities(self, text):
        """Replace characters with their character entity references.

        Only characters corresponding to a named entity are replaced.
        """
        return unicode(text).translate(self.codepoint2entity)

    def __escape(self, m):
        codepoint = ord(m.group())
        try:
            return self.codepoint2entity[codepoint]
        except (KeyError, IndexError):
            return '&#x%X;' % codepoint


    __escapable = re.compile(r'["&<>]|[^\x00-\x7f]')

    def escape(self, text):
        """Replace characters with their character references.

        Replace characters by their named entity references.
        Non-ASCII characters, if they do not have a named entity reference,
        are replaced by numerical character references.

        The return value is guaranteed to be ASCII.
        """
        return self.__escapable.sub(self.__escape, unicode(text)
                                    ).encode('ascii')

    # XXX: This regexp will not match all valid XML entity names__.
    # (It punts on details involving involving CombiningChars and Extenders.)
    #
    # .. __: http://www.w3.org/TR/2000/REC-xml-20001006#NT-EntityRef
    __characterrefs = re.compile(r'''& (?:
                                          \#(\d+)
                                          | \#x([\da-f]+)
                                          | ( (?!\d) [:\w] [-.:\w]+ )
                                          ) ;''',
                                 re.X | re.UNICODE)
    
    def __unescape(self, m):
        dval, hval, name = m.groups()
        if dval:
            codepoint = int(dval)
        elif hval:
            codepoint = int(hval, 16)
        else:
            codepoint = self.name2codepoint.get(name, 0xfffd)
            # U+FFFD = "REPLACEMENT CHARACTER"
        if codepoint < 128:
            return chr(codepoint)
        return unichr(codepoint)
    
    def unescape(self, text):
        """Unescape character references.

        All character references (both entity references and numerical
        character references) are unescaped.
        """
        return self.__characterrefs.sub(self.__unescape, text)


_html_entities_escaper = XMLEntityEscaper(htmlentitydefs.codepoint2name,
                                          htmlentitydefs.name2codepoint)

html_entities_escape = _html_entities_escaper.escape_entities
html_entities_unescape = _html_entities_escaper.unescape


def htmlentityreplace_errors(ex):
    """An encoding error handler.

    This python `codecs`_ error handler replaces unencodable
    characters with HTML entities, or, if no HTML entity exists for
    the character, XML character references.

    >>> u'The cost was \u20ac12.'.encode('latin1', 'htmlentityreplace')
    'The cost was &euro;12.'
    """
    if isinstance(ex, UnicodeEncodeError):
        # Handle encoding errors
        bad_text = ex.object[ex.start:ex.end]
        text = _html_entities_escaper.escape(bad_text)
        return (unicode(text), ex.end)
    raise ex

codecs.register_error('htmlentityreplace', htmlentityreplace_errors)


# TODO: options to make this dynamic per-compilation will be added in a later release
DEFAULT_ESCAPES = {
    'x':'filters.xml_escape',
    'h':'filters.html_escape',
    'u':'filters.url_escape',
    'trim':'filters.trim',
    'entity':'filters.html_entities_escape',
    'unicode':'unicode',
    'decode':'decode',
    'str':'str',
    'n':'n'
}
    

