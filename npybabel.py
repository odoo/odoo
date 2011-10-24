#!/usr/bin/python
# EASY-INSTALL-ENTRY-SCRIPT: 'Babel==0.9.6','console_scripts','pybabel'
__requires__ = 'Babel==0.9.6'
import sys
from pkg_resources import load_entry_point
import re
import json
import xml.etree.ElementTree as elt

if __name__ == '__main__':
    sys.exit(
        load_entry_point('Babel==0.9.6', 'console_scripts', 'pybabel')()
    )
    
XMLJS_EXPR = re.compile(r"""(?:\_t *\( *((?:"(?:[^"\\]|\\.)*")|(?:'(?:[^'\\]|\\.)*')) *\))""")

def extract_xmljs(fileobj, keywords, comment_tags, options):
    content = fileobj.read()
    found = XMLJS_EXPR.finditer(content)
    result = []
    index = 0
    line_nbr = 0
    for f in found:
        mes = f.group(1)
        mes = json.loads(mes)
        while index < f.start():
            if content[index] == "\n":
                line_nbr += 1
            index += 1
        result.append((line_nbr, None, mes, ""))
    return result

def extract_qweb(fileobj, keywords, comment_tags, options):
    """Extract messages from XXX files.
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
    def handle_text(str):
        str = (str or "").strip()
        if not str:
            return
        result.append((0, None, str, ""))
    
    def iter_elements(current_element):
        for el in current_element:
            if "t-js" not in el.attrib and \
                    not ("t-jquery" in el.attrib and "t-operation" not in el.attrib) and \
                    not ("t-translation" in el.attrib and el.attrib["t-translation"].strip() == "off"):
                handle_text(el.text)
                iter_elements(el)
            handle_text(el.tail)
    
    tree = elt.parse(fileobj)
    iter_elements(tree.getroot())

    return result
