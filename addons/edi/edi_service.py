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

import openerp

_logger = logging.getLogger(__name__)

# TODO this is not needed anymore:
# - the exposed new service just forward to the model service
# - the service is called by the web controller, which can
# now directly call into openerp as the web server is always
# embedded in openerp.

def _edi_dispatch(db_name, method_name, *method_args):
    try:
        registry = openerp.modules.registry.RegistryManager.get(db_name)
        assert registry, 'Unknown database %s' % db_name
        with registry.cursor() as cr:
            edi = registry['edi.edi']
            return getattr(edi, method_name)(cr, *method_args)

    except Exception, e:
        _logger.exception('Failed to execute EDI method %s with args %r.',
            method_name, method_args)
        raise

def exp_import_edi_document(db_name, uid, passwd, edi_document, context=None):
    return _edi_dispatch(db_name, 'import_edi', uid, edi_document, None)

def exp_import_edi_url(db_name, uid, passwd, edi_url, context=None):
    return _edi_dispatch(db_name, 'import_edi', uid, None, edi_url)

def dispatch(method, params):
    if method in ['import_edi_document',  'import_edi_url']:
        (db, uid, passwd) = params[0:3]
        openerp.service.security.check(db, uid, passwd)
    else:
        raise KeyError("Method not found: %s." % method)
    fn = globals()['exp_' + method]
    return fn(*params)

openerp.service.wsgi_server.register_rpc_endpoint('edi', dispatch)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
