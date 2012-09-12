###############################################################################
#
# Copyright (C) 2007-TODAY Tiny ERP Pvt Ltd. All Rights Reserved.
#
# $Id$
#
# Developed by Tiny (http://openerp.com) and Axelor (http://axelor.com).
#
# The OpenERP web client is distributed under the "OpenERP Public License".
# It's based on Mozilla Public License Version (MPL) 1.1 with following
# restrictions:
#
# -   All names, links and logos of Tiny, OpenERP and Axelor must be
#     kept as in original distribution without any changes in all software
#     screens, especially in start-up page and the software header, even if
#     the application source code has been changed or updated or code has been
#     added.
#
# -   All distributions of the software must keep source code with OEPL.
#
# -   All integrations to any other software must keep source code with OEPL.
#
# If you need commercial licence to remove this kind of restriction please
# contact us.
#
# You can see the MPL licence at: http://www.mozilla.org/MPL/MPL-1.1.html
#
###############################################################################

import re

import cherrypy
import wikimarkup

from openobject import rpc
from openobject.widgets import CSSLink


from openerp.widgets import register_widget
from openerp.widgets.form import Text


_image = re.compile(r'img:(.*)\.(.*)', re.UNICODE)
_rss = re.compile(r'rss:(.*)\.(.*)', re.UNICODE)
_attach = re.compile(r'attach:(.*)\.(.*)', re.UNICODE)
_internalLinks = re.compile(r'\[\[.*\]\]', re.UNICODE)
_edit = re.compile(r'edit:(.*)\|(.*)', re.UNICODE)
_view = re.compile(r'view:(.*)\|(.*)', re.UNICODE)

class WikiParser(wikimarkup.Parser):

    def parse(self, text, id):
        text = text.replace('&nbsp;', 'n-b-s-p')
        text = text.replace('&amp;', 'n-a-m-p')
        text = text.replace('&','&amp;')
        text = text.replace('n-b-s-p', '&nbsp;')
        text = text.replace('n-a-m-p', '&amp;')
        text = text.replace('<code>', '<pre>')
        text = text.replace('</code>', '</pre>')

        text = wikimarkup.to_unicode(text)
        text = self.strip(text)

        text = super(WikiParser, self).parse(text)
        text = self.addImage(text, id)
        text = self.attachDoc(text, id)
        text = self.recordLink(text)
        text = self.viewRecordLink(text)
        text = self.addInternalLinks(text)
        #TODO : already implemented but we will implement it later after releasing the 5.0
        #text = self.addRss(text, id)
        return text

    def viewRecordLink(self, text):
        def record(path):
            record = path.group().replace('view:','').split("|")
            model = record[0]
            text = record[1].replace('\r','').strip()
            label = "View Record"
            if len(record) > 2:
                label = record[2]
            proxy = rpc.RPCProxy(model)
            ids = proxy.name_search(text, [], 'ilike', {})
            if len(ids):
                id = ids[0][0]
            else:
                try:
                    id = int(text)
                except:
                    id = 0
            return "[[/openerp/form/view?model=%s&amp;id=%d | %s]]" % (model, id, label)

        bits = _view.sub(record, text)
        return bits

    def addRss(self, text, id):
        def addrss(path):
            rssurl = path.group().replace('rss:','')
            import rss.feedparser as feedparser
            data = feedparser.parse(rssurl)
            values = "<h2>%s</h2><br/>" % (data.feed.title)
            values += "%s<br/>" % (data.channel.description)
            for entry in data['entries']:
                values += "<h3><a href='%s'> %s </a></h3><br/>" % (entry.link, entry.title)
                values += "%s <br/>" % (entry.summary)

            return values

        bits = _rss.sub(addrss, text)
        return bits

    def attachDoc(self, text, id):
        def document(path):
            file = path.group().replace('attach:','')
            if file.startswith('http') or file.startswith('ftp'):
                return "<a href='%s'>Download File</a>" % (file)
            else:
                proxy = rpc.RPCProxy('ir.attachment')
                ids = proxy.search([('datas_fname','=',file.strip()), ('res_model','=','wiki.wiki'), ('res_id','=',id)])
                if len(ids) > 0:
                    return "<a href='/widget_wiki/wiki/getfile?file=%s&amp;id=%d'>%s</a>" % (file, id, file)
                else:
                    return """<a onclick="openobject.tools.openWindow(openobject.http.getURL('/openerp/attachment', {model: 'wiki.wiki', id: %d}),
                    {name : 'Wiki Attachments'})">Attach : %s </a>""" % (id, file)
        bits = _attach.sub(document, text)
        return bits

    def addImage(self, text, id):
        def image(path):
            file = path.group().replace('img:','')
            if file.startswith('http') or file.startswith('ftp'):
                return "<img src='%s'/>" % (file)
            else:
                proxy = rpc.RPCProxy('ir.attachment')
                ids = proxy.search([('datas_fname','=',file.strip()), ('res_model','=','wiki.wiki'), ('res_id','=',id)])
                if len(ids) > 0:
                    return "<img src='/widget_wiki/wiki/getImage?file=%s&amp;id=%d'/>" % (file, id)
                else:
                    return """<a onclick="openobject.tools.openWindow(openobject.http.getURL('/openerp/attachment', {model: 'wiki.wiki', id: %d}),
                    {name : 'Wiki Attachments'})">Attach : %s </a>""" % (id, file)
                #"[[/attachment/?model=wiki.wiki&amp;id=%d | Attach:%s]]" % (id, file)
        bits = _image.sub(image, text)
        return bits

    def recordLink(self, text):
        def record(path):
            record = path.group().replace('edit:','').split("|")
            model = record[0]
            text = record[1].replace('\r','').strip()
            label = "Edit Record"
            if len(record) > 2:
                label = record[2]
            proxy = rpc.RPCProxy(model)
            ids = proxy.name_search(text, [], '=', {})
            if len(ids):
                id = ids[0][0]
            else:
                try:
                    id = int(text)
                except:
                    id = 0
            return "[[/openerp/form/edit?model=%s&amp;id=%d | %s]]" % (model, id, label)

        bits = _edit.sub(record, text)
        return bits

    def addInternalLinks(self, text):
        proxy = rpc.RPCProxy('wiki.wiki')
        
        def link(path):
            link = path.group().replace('[','').replace('[','').replace(']','').replace(']','').split("|")
            name_to_search = link[0].strip()
            mids = proxy.search([('name','ilike', name_to_search)])
            link_str = ""
            if mids:
               if len(link) == 2:
                   link_str = "<a href='/openerp/form/view?model=wiki.wiki&amp;id=%s'>%s</a>" % (mids[0], link[1])
               elif len(link) == 1:
                   link_str = "<a href='/openerp/form/view?model=wiki.wiki&amp;id=%s'>%s</a>" % (mids[0], link[0])
            else:
                if len(link) == 2:
                    link_str = "<a href='%s'>%s</a>" % (link[0], link[1])
                elif len(link) == 1:
                    link_str = "<a href='/openerp/form/edit?model=wiki.wiki&amp;id=False'>%s</a>" % (link[0])

            return link_str

        bits = _internalLinks.sub(link, text)
        return bits

def wiki2html(text, showToc, id):
    p = WikiParser(show_toc=showToc)
    return p.parse(text, id)

class WikiWidget(Text):
    template = "/wiki/widgets/templates/wiki.mako"

    params = ["data"]

    css = [CSSLink("wiki", "css/wiki.css")]

    data = None

    def set_value(self, value):
        super(WikiWidget, self).set_value(value)

        if value:
            toc = True
            id = False
            if hasattr(cherrypy.request, 'terp_record'):
                params = cherrypy.request.terp_params
                if params._terp_model == 'wiki.wiki':
                    proxy = rpc.RPCProxy('wiki.wiki')
                    toc = proxy.read([params.id], ['toc'])[0]['toc']
                    id = params.id

            text = value+'\n\n'
            html = wiki2html(text, toc, id)

            self.data = html

register_widget(WikiWidget, ["text_wiki"])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
