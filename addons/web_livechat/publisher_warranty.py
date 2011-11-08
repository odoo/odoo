# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2011 OpenERP s.a. (<http://openerp.com>).
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

from osv import osv
from tools import cache

def _gen_cache_clear(method):
    def func(self, cr, *args, **kwargs):
        s = super(publisher_warranty_contract, self)
        r = getattr(s, method)(cr, *args, **kwargs)
        self.is_livechat_enable.clear_cache(cr.dbname)
        return r
    return func

class publisher_warranty_contract(osv.osv):
    _inherit = 'publisher_warranty.contract'

    create = _gen_cache_clear('create')
    write = _gen_cache_clear('write')
    unlink = _gen_cache_clear('unlink')

    @cache(skiparg=3, timeout=300)
    def is_livechat_enable(self, cr, uid):
        domain = [('state', '=', 'valid'), ('check_support', '=', True)]
        return self.search_count(cr, uid, domain) != 0

    @cache(skiparg=3)
    def get_default_livechat_text(self, cr, uid):
        return '<a href="http://www.openerp.com/support-or-publisher-warranty-contract" target="_blank"><img src="/web_livechat/static/src/img/busy.png"/>Support</a>'

publisher_warranty_contract()

