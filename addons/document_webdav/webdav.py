# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (c) 1999 Christian Scholz (ruebe@aachen.heimat.de)
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

import xml.dom.minidom
domimpl = xml.dom.minidom.getDOMImplementation()
from xml.dom.minicompat import StringTypes

import urlparse
import urllib
from osv import osv
from tools.translate import _

try:
    from DAV import utils
    from DAV.propfind import PROPFIND
    from DAV.report import REPORT
except ImportError:
    raise osv.except_osv(_('PyWebDAV Import Error!'), _('Please install PyWebDAV from http://code.google.com/p/pywebdav/downloads/detail?name=PyWebDAV-0.9.4.tar.gz&can=2&q=/'))

import tools

class Text2(xml.dom.minidom.Text):
    def writexml(self, writer, indent="", addindent="", newl=""):
        data = "%s%s%s" % (indent, self.data, newl)
        data = data.replace("&", "&amp;").replace("<", "&lt;")
        data = data.replace(">", "&gt;")
        writer.write(data)

class Prop2xml(object):
    """ A helper class to convert property structs to DAV:XML
    
        Written to generalize the use of _prop_child(), a class is 
        needed to hold some persistent data accross the recursions 
        of _prop_elem_child().
    """
    
    def __init__(self, doc, namespaces, nsnum):
        """ Init the structure
        @param doc the xml doc element
        @param namespaces a dict of namespaces
        @param nsnum the next namespace number to define
        """
        self.doc = doc
        self.namespaces = namespaces
        self.nsnum = nsnum

    def createText2Node(self, data):
        if not isinstance(data, StringTypes):
            raise TypeError, "node contents must be a string"
        t = Text2()
        t.data = data
        t.ownerDocument = self.doc
        return t

    def _prop_child(self, xnode, ns, prop, value):
        """Append a property xml node to xnode, with <prop>value</prop>

           And a little smarter than that, it will consider namespace and
           also allow nested properties etc.

           :param ns the namespace of the <prop/> node
           :param prop the name of the property
           :param value the value. Can be:
                    string: text node
                    tuple ('elem', 'ns') for empty sub-node <ns:elem />
                    tuple ('elem', 'ns', sub-elems) for sub-node with elements
                    tuple ('elem', 'ns', sub-elems, {attrs}) for sub-node with 
                            optional elements and attributes
                    list, of above tuples
        """
        if ns == 'DAV:':
            ns_prefix = 'D:'
        else:
            ns_prefix="ns"+str(self.namespaces.index(ns))+":"

        pe = self.doc.createElement(ns_prefix+str(prop))
        if hasattr(value, '__class__') and value.__class__.__name__ == 'Element':
            pe.appendChild(value)
        else:
            if ns == 'DAV:' and prop=="resourcetype" and isinstance(value, int):
                # hack, to go..
                if value == 1:
                    ve = self.doc.createElement("D:collection")
                    pe.appendChild(ve)
            else:
                self._prop_elem_child(pe, ns, value, ns_prefix)

            xnode.appendChild(pe)

    def _prop_elem_child(self, pnode, pns, v, pns_prefix):

        if isinstance(v, list):
            for vit in v:
                self._prop_elem_child(pnode, pns, vit, pns_prefix)
        elif isinstance(v,tuple):
            need_ns = False
            if v[1] == pns:
                ns_prefix = pns_prefix
            elif v[1] == 'DAV:':
                ns_prefix = 'D:'
            elif v[1] in self.namespaces:
                ns_prefix="ns"+str(self.namespaces.index(v[1]))+":"
            else:
                ns_prefix="ns"+str(self.nsnum)+":"
                need_ns = True

            ve = self.doc.createElement(ns_prefix+v[0])
            if need_ns:
                ve.setAttribute("xmlns:ns"+str(self.nsnum), v[1])
            if len(v) > 2 and v[2] is not None:
                if isinstance(v[2], (list, tuple)):
                    # support nested elements like:
                    # ( 'elem', 'ns:', [('sub-elem1', 'ns1'), ...]
                    self._prop_elem_child(ve, v[1], v[2], ns_prefix)
                else:
                    vt = self.createText2Node(tools.ustr(v[2]))
                    ve.appendChild(vt)
            if len(v) > 3 and v[3]:
                assert isinstance(v[3], dict)
                for ak, av in v[3].items():
                    ve.setAttribute(ak, av)
            pnode.appendChild(ve)
        else:
            ve = self.createText2Node(tools.ustr(v))
            pnode.appendChild(ve)


super_mk_prop_response = PROPFIND.mk_prop_response
def mk_prop_response(self, uri, good_props, bad_props, doc):
    """ make a new <prop> result element

    We differ between the good props and the bad ones for
    each generating an extra <propstat>-Node (for each error
    one, that means).

    """
    re=doc.createElement("D:response")
    # append namespaces to response
    nsnum=0
    namespaces = self.namespaces[:]
    if 'DAV:' in namespaces:
        namespaces.remove('DAV:')
    for nsname in namespaces:
        re.setAttribute("xmlns:ns"+str(nsnum),nsname)
        nsnum=nsnum+1

    propgen = Prop2xml(doc, namespaces, nsnum)
    # write href information
    uparts=urlparse.urlparse(uri)
    fileloc=uparts[2]
    if uparts[3]:
        fileloc += ';' + uparts[3]
    if isinstance(fileloc, unicode):
        fileloc = fileloc.encode('utf-8')
    href=doc.createElement("D:href")
    davpath = self._dataclass.parent.get_davpath()
    if uparts[0] and uparts[1]:
        hurl = '%s://%s%s%s' % (uparts[0], uparts[1], davpath, urllib.quote(fileloc))
    else:
        # When the request has been relative, we don't have enough data to
        # reply with absolute url here.
        hurl = '%s%s' % (davpath, urllib.quote(fileloc))
    huri=doc.createTextNode(hurl)
    href.appendChild(huri)
    re.appendChild(href)

    # write good properties
    ps=doc.createElement("D:propstat")
    if good_props:
        re.appendChild(ps)
    s=doc.createElement("D:status")
    t=doc.createTextNode("HTTP/1.1 200 OK")
    s.appendChild(t)
    ps.appendChild(s)

    gp=doc.createElement("D:prop")
    for ns in good_props.keys():
        if ns == 'DAV:':
            ns_prefix = 'D:'
        else:
            ns_prefix="ns"+str(namespaces.index(ns))+":"
        for p,v in good_props[ns].items():
            if v is None:
                continue
            propgen._prop_child(gp, ns, p, v)

    ps.appendChild(gp)
    re.appendChild(ps)

    # now write the errors!
    if len(bad_props.items()):

        # write a propstat for each error code
        for ecode in bad_props.keys():
            ps=doc.createElement("D:propstat")
            re.appendChild(ps)
            s=doc.createElement("D:status")
            t=doc.createTextNode(utils.gen_estring(ecode))
            s.appendChild(t)
            ps.appendChild(s)
            bp=doc.createElement("D:prop")
            ps.appendChild(bp)

            for ns in bad_props[ecode].keys():
                if ns == 'DAV:':
                    ns_prefix='D:'
                else:
                    ns_prefix="ns"+str(self.namespaces.index(ns))+":"

            for p in bad_props[ecode][ns]:
                pe=doc.createElement(ns_prefix+str(p))
                bp.appendChild(pe)

            re.appendChild(ps)

    # return the new response element
    return re


def mk_propname_response(self,uri,propnames,doc):
    """ make a new <prop> result element for a PROPNAME request

    This will simply format the propnames list.
    propnames should have the format {NS1 : [prop1, prop2, ...], NS2: ...}

    """
    re=doc.createElement("D:response")

    # write href information
    uparts=urlparse.urlparse(uri)
    fileloc=uparts[2]
    if uparts[3]:
        fileloc += ';' + uparts[3]
    if isinstance(fileloc, unicode):
        fileloc = fileloc.encode('utf-8')
    href=doc.createElement("D:href")
    davpath = self._dataclass.parent.get_davpath()
    if uparts[0] and uparts[1]:
        hurl = '%s://%s%s%s' % (uparts[0], uparts[1], davpath, urllib.quote(fileloc))
    else:
        # When the request has been relative, we don't have enough data to
        # reply with absolute url here.
        hurl = '%s%s' % (davpath, urllib.quote(fileloc))
    huri=doc.createTextNode(hurl)
    href.appendChild(huri)
    re.appendChild(href)

    ps=doc.createElement("D:propstat")
    nsnum=0

    for ns,plist in propnames.items():
        # write prop element
        pr=doc.createElement("D:prop")
        if ns == 'DAV':
            nsp = 'D'
        else:
            nsp="ns"+str(nsnum)
            ps.setAttribute("xmlns:"+nsp,ns)
            nsnum=nsnum+1

        # write propertynames
        for p in plist:
            pe=doc.createElement(nsp+":"+p)
            pr.appendChild(pe)

        ps.appendChild(pr)

    re.appendChild(ps)

    return re

PROPFIND.mk_prop_response = mk_prop_response
PROPFIND.mk_propname_response = mk_propname_response

def mk_lock_response(self, uri, props):
    """ Prepare the data response to a DAV LOCK command
    
    This function is here, merely to be in the same file as the
    ones above, that have similar code.
    """
    doc = domimpl.createDocument('DAV:', "D:prop", None)
    ms = doc.documentElement
    ms.setAttribute("xmlns:D", "DAV:")
    # ms.tagName = 'D:multistatus'
    namespaces = []
    nsnum = 0
    propgen = Prop2xml(doc, namespaces, nsnum)
    # write href information
    uparts=urlparse.urlparse(uri)
    fileloc=uparts[2]
    if uparts[3]:
        fileloc += ';' + uparts[3]
    if isinstance(fileloc, unicode):
        fileloc = fileloc.encode('utf-8')
    davpath = self.parent.get_davpath()
    if uparts[0] and uparts[1]:
        hurl = '%s://%s%s%s' % (uparts[0], uparts[1], davpath, urllib.quote(fileloc))
    else:
        # When the request has been relative, we don't have enough data to
        # reply with absolute url here.
        hurl = '%s%s' % (davpath, urllib.quote(fileloc))
        
    props.append( ('lockroot', 'DAV:', ('href', 'DAV:', (hurl))))
    pld = doc.createElement('D:lockdiscovery')
    ms.appendChild(pld)
    propgen._prop_child(pld, 'DAV:', 'activelock', props)

    return doc.toxml(encoding="utf-8")

super_create_prop = REPORT.create_prop

def create_prop(self):
    try:
        if (self.filter is not None) and self._depth == "0":
            hrefs = self.filter.getElementsByTagNameNS('DAV:', 'href')
            if hrefs:
                self._depth = "1"
    except Exception:
        pass
    return super_create_prop(self)

REPORT.create_prop = create_prop

#eof
