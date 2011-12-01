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

import openerp.exceptions
import openerp.pooler as pooler
import openerp.tools as tools

#.apidoc title: Authentication helpers

def login(db, login, password):
    pool = pooler.get_pool(db)
    user_obj = pool.get('res.users')
    return user_obj.login(db, login, password)

def check_super(passwd):
    if passwd == tools.config['admin_passwd']:
        return True
    else:
        raise openerp.exceptions.AccessDenied()

def check(db, uid, passwd):
    pool = pooler.get_pool(db)
    user_obj = pool.get('res.users')
    return user_obj.check(db, uid, passwd)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
