# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import xmlrpclib
import config
import logging
import pooler

_logger = logging.getLogger(__name__)

class RemoteConnectionException(Exception):
    pass

class RemoteConnection:
    
    def __init__(self, server, db, login, password):
        self._server = server.strip()
        if not self._server.endswith("/"):
            self._server += "/"
        self._db = db
        self._login = login
        self._password = password
        
        rpc = xmlrpclib.ServerProxy(self._server + "xmlrpc/common")
        try:
            self._userid = rpc.login(self._db, self._login, self._password)
        except:
            raise RemoteConnectionException("Unable to contact the remote server")

        if not self._userid:
            raise RemoteConnectionException("Unable to contact the remote server")
        
        self._rpc = xmlrpclib.ServerProxy(self._server + "xmlrpc/object")
        
    def get_remote_object(self, object):
        return RemoteObject(self, object)
    
class RemoteObject(object):
    
    def __init__(self, connection, object):
        self._c = connection
        self._object = object
    
    def __getattr__(self, fun):
        def remote_call(*args, **kwargs):
            return self._c._rpc.execute(self._c._db, self._c._userid,
                                          self._c._password, self._object, fun, *args, **kwargs)
        return remote_call
    
    def __getitem__(self, item):
        return getattr(self, item)
        
class RemoteContractException(Exception): pass

def remote_contract(cr, uid, contract_id):
    pool = pooler.get_pool(cr.dbname)
    dbuuid = pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')
    
    try:
        ro = RemoteConnection(config.config.get("maintenance_server"), config.config.get("maintenance_db"),
                              config.config.get("maintenance_login"), config.config.get("maintenance_password")
                              ).get_remote_object('maintenance.maintenance')
    except:
        _logger.exception("Exception")
        raise RemoteContractException("Unable to contact the migration server")

    info = ro.check_contract({
                "contract_name": contract_id,
                "dbuuid": dbuuid,
                "dbname": cr.dbname})
    for n in info:
        setattr(ro, n, info[n])
    
    return ro


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

