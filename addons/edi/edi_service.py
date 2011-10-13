# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2011 OpenERP S.A. <http://openerp.com>
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
import logging

import netsvc
import openerp

_logger = logging.getLogger('edi.service')

class edi(netsvc.ExportService):

    def __init__(self, name="edi"):
        netsvc.ExportService.__init__(self, name)

    def _edi_dispatch(self, db_name, method_name, *method_args):
        try:
            registry = openerp.modules.registry.RegistryManager.get(db_name)
            assert registry, 'Unknown database %s' % db_name
            edi_document = registry['edi.document']
            cr = registry.db.cursor()
            res = None
            res = getattr(edi_document, method_name)(cr, *method_args)
            cr.commit()
        except Exception:
            _logger.exception('Failed to execute EDI method %s with args %r', method_name, method_args)
            cr.rollback()
        finally:
            cr.close()
        return res

    def exp_get_edi_document(self, db_name, edi_token):
        return self._edi_dispatch(db_name, 'get_document', 1, edi_token)

    def exp_import_edi_document(self, db_name, uid, passwd, edi_document, context=None):
        return self._edi_dispatch(db_name, 'import_edi', uid, edi_document, None)

    def exp_import_edi_url(self, db_name, uid, passwd, edi_url, context=None):
        return self._edi_dispatch(db_name, 'import_edi', uid, None, edi_url)

    def dispatch(self, method, params):
        if method in ['import_edi_document',  'import_edi_url']:
            (db, uid, passwd ) = params[0:3]
            openerp.service.security.check(db, uid, passwd)
        elif method in ['get_edi_document']:
            # No security check for these methods
            pass
        else:
            raise KeyError("Method not found: %s" % method)
        fn = getattr(self, 'exp_'+method)
        return fn(*params)

edi()