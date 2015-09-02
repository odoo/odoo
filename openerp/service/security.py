# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
import openerp.exceptions

def login(db, login, password):
    res_users = openerp.registry(db)['res.users']
    return res_users._login(db, login, password)

def check(db, uid, passwd):
    res_users = openerp.registry(db)['res.users']
    return res_users.check(db, uid, passwd)
