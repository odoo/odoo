# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import xmlrpclib

class remote_contract(object):
    def __init__(self, contract_id, contract_password, modules=None):
        self.__server = 'http://localhost:8069/xmlrpc/'
        self.__db = "trunk"
        self.__password = "admin"
        self.__login = "admin"
        
        rpc = xmlrpclib.ServerProxy(self.__server + 'common')
        self.__userid = rpc.login(self.__db, self.__login, self.__password)

        self.__rpc = xmlrpclib.ServerProxy(self.__server + 'object')
        

        contract = {
            'name': contract_id,
            'password': contract_password,
        }
        if modules is None:
            modules = []

        info = self.check_contract(modules, contract)
        for n in info:
            setattr(self, n, info[n])
        
        self.name = contract_id
        self.contract_id = self.name
        self.password = contract_password
        
    def __getattr__(self, fun):
        def remote_call(*args, **kwargs):
            return self.__rpc.execute(self.__db, self.__userid, self.__password, 'maintenance.maintenance', fun, *args, **kwargs)
        return remote_call

    def __getitem__(self, item):
        return getattr(self, item)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

