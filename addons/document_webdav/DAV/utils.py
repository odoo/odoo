#!/usr/bin/env python

"""

UTILITIES

- parse a propfind request body into a list of props

"""

from xml.dom import ext
from xml.dom.Document import Document
from xml.dom.ext.reader import PyExpat
from xml.dom import Node
from xml.dom import NodeIterator, NodeFilter

from string import lower, split, atoi, joinfields
import urlparse
from StringIO import StringIO

from constants import RT_ALLPROP, RT_PROPNAME, RT_PROP
from status import STATUS_CODES

VERSION = '0.6'
AUTHOR  = 'Simon Pamies <s.pamies@banality.de>'


def gen_estring(ecode):
    """ generate an error string from the given code """
    ec=atoi(str(ecode))
    if STATUS_CODES.has_key(ec):
        return "HTTP/1.1 %s %s" %(ec,STATUS_CODES[ec])
    else:
        return "HTTP/1.1 %s" %(ec)

def parse_propfind(xml_doc):
    """ parse an propfind xml file and return a list of props

    returns:

        request_type            -- ALLPROP, PROPNAME, PROP
        proplist            -- list of properties found
        namespaces            -- list of namespaces found

    """
    doc = PyExpat.Reader().fromString(xml_doc)
    snit = doc.createNodeIterator(doc, NodeFilter.NodeFilter.SHOW_ELEMENT, None, None)

    request_type=None
    props={}
    namespaces=[]

    while 1:
        curr_elem = snit.nextNode()
        if not curr_elem: break
        ename=fname=lower(curr_elem.nodeName)
        if ":" in fname:
            ename=split(fname,":")[1]
        if ename=="prop": request_type=RT_PROP; continue
        if ename=="propfind": continue
        if ename=="allprop": request_type=RT_ALLPROP; continue
        if ename=="propname": request_type=RT_PROPNAME; continue

        # rest should be names of attributes

        ns = curr_elem.namespaceURI
        if props.has_key(ns):
            props[ns].append(ename)
        else:
            props[ns]=[ename]
            namespaces.append(ns)

    return request_type,props,namespaces


def create_treelist(dataclass,uri):
    """ create a list of resources out of a tree

    This function is used for the COPY, MOVE and DELETE methods

    uri - the root of the subtree to flatten

    It will return the flattened tree as list

    """
    queue=[uri]
    list=[uri]
    while len(queue):
        element=queue[-1]
        if dataclass.is_collection(element):
            childs=dataclass.get_childs(element)
        else:
            childs=[]
        if len(childs):
            list=list+childs
        # update queue
        del queue[-1]
        if len(childs):
            queue=queue+childs
    return list

def is_prefix(uri1,uri2):
    """ returns 1 of uri1 is a prefix of uri2 """
    if uri2[:len(uri1)]==uri1:
        return 1
    else:
        return None

def quote_uri(uri):
    """ quote an URL but not the protocol part """
    import urlparse
    import urllib

    up=urlparse.urlparse(uri)
    np=urllib.quote(up[2])
    return urlparse.urlunparse((up[0],up[1],np,up[3],up[4],up[5]))

def get_uriparentpath(uri):
    """ extract the uri path and remove the last element """
    up=urlparse.urlparse(uri)
    return joinfields(split(up[2],"/")[:-1],"/")

def get_urifilename(uri):
    """ extract the uri path and return the last element """
    up=urlparse.urlparse(uri)
    return split(up[2],"/")[-1]

def get_parenturi(uri):
    """ return the parent of the given resource"""
    up=urlparse.urlparse(uri)
    np=joinfields(split(up[2],"/")[:-1],"/")
    return urlparse.urlunparse((up[0],up[1],np,up[3],up[4],up[5]))

### XML utilities

def make_xmlresponse(result):
    """ construct a response from a dict of uri:error_code elements """
    doc = Document.Document(None)
    ms=doc.createElement("D:multistatus")
    ms.setAttribute("xmlns:D","DAV:")
    doc.appendChild(ms)

    for el,ec in result.items():
        re=doc.createElement("D:response")
        hr=doc.createElement("D:href")
        st=doc.createElement("D:status")
        huri=doc.createTextNode(quote_uri(el))
        t=doc.createTextNode(gen_estring(ec))
        st.appendChild(t)
        hr.appendChild(huri)
        re.appendChild(hr)
        re.appendChild(st)
        ms.appendChild(re)

    sfile=StringIO()
    ext.PrettyPrint(doc,stream=sfile)
    s=sfile.getvalue()
    sfile.close()
    return s

