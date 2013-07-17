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
import base64

import cherrypy

import openobject
from openobject.tools import expose

from openerp.controllers import SecuredController


class WikiView(SecuredController):
    _cp_path = "/wiki/wiki"

    def get_attachment(self, **kwargs):
        attachments = openobject.rpc.RPCProxy('ir.attachment')
        file_name = kwargs.get('file').replace("'", '').strip()
        id = kwargs.get('id').strip()

        ids = attachments.search([('datas_fname', '=', file_name),
                                  ('res_model', '=', 'wiki.wiki'),
                                  ('res_id', '=', id)])

        res = attachments.read(ids, ['datas'])[0].get('datas')
        return res, file_name

    @expose(content_type='application/octet')
    def getImage(self, *kw, **kws):
        res, _ = self.get_attachment(**kws)
        return base64.decodestring(res)

    @expose(content_type='application/octet')
    def getfile(self, *kw, **kws):
        res, file_name = self.get_attachment(**kws)
        cherrypy.response.headers['Content-Disposition'] = 'filename="%s"' % (file_name,)
        return base64.decodestring(res)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
