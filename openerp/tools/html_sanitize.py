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

import lxml.html
import operator
import re

from openerp.loglevels import ustr

def html_sanitize(src):
    if not src:
        return src
    src = ustr(src, errors='replace')
    root = lxml.html.fromstring(u"<div>%s</div>" % src)
    result = handle_element(root)
    res = []
    for element in children(result[0]):
        if isinstance(element, basestring):
            res.append(element)
        else:
            element.tail = ""
            res.append(lxml.html.tostring(element))
    return ''.join(res)

# FIXME: shouldn't this be a whitelist rather than a blacklist?!
to_remove = set(["script", "head", "meta", "title", "link", "img"])
to_unwrap = set(["html", "body"])

javascript_regex = re.compile(r"^\s*javascript\s*:.*$", re.IGNORECASE)

def handle_a(el, new):
    href = el.get("href", "#")
    if javascript_regex.search(href):
        href = "#"
    new.set("href", href)

special = {
    "a": handle_a,
}

def handle_element(element):
    if isinstance(element, basestring):
        return [element]
    if element.tag in to_remove:
        return []
    if element.tag in to_unwrap:
        return reduce(operator.add, [handle_element(x) for x in children(element)])
    result = lxml.html.fromstring("<%s />" % element.tag)
    for c in children(element):
        append_to(handle_element(c), result)
    if element.tag in special:
        special[element.tag](element, result)
    return [result]

def children(node):
    res = []
    if node.text is not None:
        res.append(node.text)
    for child_node in node.getchildren():
        res.append(child_node)
        if child_node.tail is not None:
            res.append(child_node.tail)
    return res

def append_to(elements, dest_node):
    for element in elements:
        if isinstance(element, basestring):
            children = dest_node.getchildren()
            if len(children) == 0:
                dest_node.text = element
            else:
                children[-1].tail = element
        else:
            dest_node.append(element)
