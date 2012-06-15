#!/usr/bin/env python
# EASY-INSTALL-ENTRY-SCRIPT: 'Babel==0.9.6','console_scripts','pybabel'
__requires__ = 'Babel==0.9.6'
import sys
from pkg_resources import load_entry_point
import re
import json
from lxml import etree as elt
from babel.messages import extract

if __name__ == '__main__':
    sys.exit(
        load_entry_point('Babel==0.9.6', 'console_scripts', 'pybabel')()
    )

XMLJS_EXPR = re.compile(r"""(?:\_t *\( *((?:"(?:[^"\\]|\\.)*")|(?:'(?:[^'\\]|\\.)*')) *\))""")

TRANSLATION_FLAG_COMMENT = "openerp-web"

# List of etree._Element subclasses that we choose to ignore when parsing XML.
# We include the *Base ones just in case, currently they seem to be subclasses of the _* ones.
SKIPPED_ELEMENT_TYPES = (elt._Comment, elt._ProcessingInstruction, elt.CommentBase, elt.PIBase)

def extract_xmljs(fileobj, keywords, comment_tags, options):
    """Extract messages from Javascript code embedded into XML documents.
    This complements the ``extract_javascript`` extractor which works
    only on pure .js files, and the``extract_qweb`` extractor, which only
    extracts XML text.

    :param fileobj: the file-like object the messages should be extracted
                    from
    :param keywords: a list of keywords (i.e. function names) that should
                     be recognized as translation functions
    :param comment_tags: a list of translator tags to search for and
                         include in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)``
             tuples
    :rtype: ``iterator``
    """
    assert False, """ the XMLJS extractor does not work and was removed:

    * Babel apparently does not accept two extractors for the same set of files
      so it would not run the xmljs extractor at all, extraction of JS stuff
      needs to be done from the XML extractor
    * The regex above fails up if there are back-slashed quotes within the
      translatable string (the string marked with _t), it just won't match the
      string
    * While extraction succeeds on XML entities (e.g. &quot;), translation
      matching will fail if those entities are kept in the PO msgid as the
      XML parser will get an un-escaped string, without those entities (so a
      text extractor will extract ``Found match &quot;%s&quot;``, but the msgid
      of the PO file must be ``Found match "%s"`` or the translation will fail
    * single-quoted strings are not valid JSON string, so single-quoted strings
      matched by the regex (likely since XML attributes are double-quoted,
      single quotes within them don't have to be escaped) will blow up when
      json-parsed for their content

    I think that's about it.

    If this extractor is reimplemented, it should be integrated into
    extract_qweb, either in the current pass (probably not a good idea) or as
    a separate pass using iterparse, matching either elements with t-js or
    some other kinds of t-* directives (@t-esc, @t-raw, @t-att, others?),
    shove the attribute content into a StringIO and pass *that* to Babel's
    own extract_javascript; then add a line offset in order to yield the
    correct line number.
    """
    content = fileobj.read()
    found = XMLJS_EXPR.finditer(content)
    index = 0
    line_nbr = 0
    for f in found:
        msg = f.group(1)
        msg = json.loads(msg)
        while index < f.start():
            if content[index] == "\n":
                line_nbr += 1
            index += 1
        yield (line_nbr, None, msg, [TRANSLATION_FLAG_COMMENT])

def extract_qweb(fileobj, keywords, comment_tags, options):
    """Extract messages from qweb template files.
    :param fileobj: the file-like object the messages should be extracted
                    from
    :param keywords: a list of keywords (i.e. function names) that should
                     be recognized as translation functions
    :param comment_tags: a list of translator tags to search for and
                         include in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)``
             tuples
    :rtype: ``iterator``
    """
    result = []
    def handle_text(text, lineno):
        text = (text or "").strip()
        if len(text) > 1: # Avoid mono-char tokens like ':' ',' etc.
            result.append((lineno, None, text, [TRANSLATION_FLAG_COMMENT]))

    # not using elementTree.iterparse because we need to skip sub-trees in case
    # the ancestor element had a reason to be skipped
    def iter_elements(current_element):
        for el in current_element:
            if isinstance(el, SKIPPED_ELEMENT_TYPES): continue
            if "t-js" not in el.attrib and \
                    not ("t-jquery" in el.attrib and "t-operation" not in el.attrib) and \
                    not ("t-translation" in el.attrib and el.attrib["t-translation"].strip() == "off"):
                handle_text(el.text, el.sourceline)
                for att in ('title', 'alt', 'label', 'placeholder'):
                    if att in el.attrib:
                        handle_text(el.attrib[att], el.sourceline)
                iter_elements(el)
            handle_text(el.tail, el.sourceline)

    tree = elt.parse(fileobj)
    iter_elements(tree.getroot())

    return result

def extract_javascript(fileobj, keywords, comment_tags, options):
    """Extract messages from Javascript source files. This extractor delegates
    to babel's buit-in javascript extractor, but adds a special comment
    used as a flag to identify web translations. 

    :param fileobj: the file-like object the messages should be extracted
                    from
    :param keywords: a list of keywords (i.e. function names) that should
                     be recognized as translation functions
    :param comment_tags: a list of translator tags to search for and
                         include in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)``
             tuples
    :rtype: ``iterator``
    """
    for (message_lineno, funcname, messages, comments) in \
        extract.extract_javascript(fileobj, keywords, comment_tags, options):
        comments.append(TRANSLATION_FLAG_COMMENT)
        yield (message_lineno, funcname, messages, comments)
