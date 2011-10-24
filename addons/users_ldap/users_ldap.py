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

from osv import fields, osv
import pooler
import tools
import logging
import ldap
from ldap.filter import filter_format

import openerp.exceptions


class CompanyLDAP(osv.osv):
    _name = 'res.company.ldap'
    _order = 'sequence'
    _rec_name = 'ldap_server'
    _columns = {
        'sequence': fields.integer('Sequence'),
        'company': fields.many2one('res.company', 'Company', required=True,
            ondelete='cascade'),
        'ldap_server': fields.char('LDAP Server address', size=64, required=True),
        'ldap_server_port': fields.integer('LDAP Server port', required=True),
        'ldap_binddn': fields.char('LDAP binddn', size=64,
            help=("The user account on the LDAP server that is used to query "
                  "the directory. Leave empty to connect anonymously.")),
        'ldap_password': fields.char('LDAP password', size=64,
            help=("The password of the user account on the LDAP server that is "
                  "used to query the directory.")),
        'ldap_filter': fields.char('LDAP filter', size=256, required=True),
        'ldap_base': fields.char('LDAP base', size=64, required=True),
        'user': fields.many2one('res.users', 'Model User',
            help="Model used for user creation"),
        'create_user': fields.boolean('Create user',
            help="Create the user if not in database"),
    }
    _defaults = {
        'ldap_server': lambda *a: '127.0.0.1',
        'ldap_server_port': lambda *a: 389,
        'sequence': lambda *a: 10,
        'create_user': lambda *a: True,
    }

CompanyLDAP()


class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'ldaps': fields.one2many('res.company.ldap', 'company', 'LDAP Parameters'),
    }
res_company()

class users(osv.osv):
    _inherit = "res.users"
    def login(self, db, login, password):

        if not password:
            # empty passwords are disallowed for obvious security reasons
            return False

        ret = super(users,self).login(db, login, password)
        if ret:
            return ret
        logger = logging.getLogger('orm.ldap')
        pool = pooler.get_pool(db)
        cr = pooler.get_db(db).cursor()
        action_obj = pool.get('ir.actions.actions')
        cr.execute("""
            SELECT id, company, ldap_server, ldap_server_port, ldap_binddn, ldap_password,
                   ldap_filter, ldap_base, "user", create_user
            FROM res_company_ldap
            WHERE ldap_server != '' ORDER BY sequence""")
        for res_company_ldap in cr.dictfetchall():
            logger.debug(res_company_ldap)
            try:
                l = ldap.open(res_company_ldap['ldap_server'], res_company_ldap['ldap_server_port'])
                # An empty binddn means anonymous auth, so it should be replaced w/ an empty string
                # See LDAP RFC 4513, Section 5.1.1
                if l.simple_bind_s(res_company_ldap['ldap_binddn'] or '',
                                   res_company_ldap['ldap_password'] or ''):
                    base = res_company_ldap['ldap_base']
                    scope = ldap.SCOPE_SUBTREE
                    filter = filter_format(res_company_ldap['ldap_filter'], (login,))
                    retrieve_attributes = None
                    result_id = l.search(base, scope, filter, retrieve_attributes)
                    timeout = 60
                    result_type, result_data = l.result(result_id, timeout)
                    if not result_data:
                        continue
                    if result_type == ldap.RES_SEARCH_RESULT and len(result_data) == 1:
                        dn = result_data[0][0]
                        logger.debug(dn)
                        name = result_data[0][1]['cn'][0]
                        if l.bind_s(dn, password):
                            l.unbind()
                            cr.execute("SELECT id FROM res_users WHERE login=%s",(tools.ustr(login),))
                            res = cr.fetchone()
                            logger.debug(res)
                            if res:
                                cr.close()
                                return res[0]
                            if not res_company_ldap['create_user']:
                                continue
                            action_id = action_obj.search(cr, 1, [('usage', '=', 'menu')])[0]
                            if res_company_ldap['user']:
                                res = self.copy(cr, 1, res_company_ldap['user'],
                                        default={'active': True})
                                self.write(cr, 1, res, {
                                    'name': name,
                                    'login': login.encode('utf-8'),
                                    'company_id': res_company_ldap['company'],
                                    })
                            else:
                                res = self.create(cr, 1, {
                                    'name': name,
                                    'login': login.encode('utf-8'),
                                    'company_id': res_company_ldap['company'],
                                    'action_id': action_id,
                                    'menu_id': action_id,
                                    })
                            cr.commit()
                            cr.close()
                            return res
                    l.unbind()
            except Exception:
                logger.warning("Cannot auth", exc_info=True)
                continue
        cr.close()
        return False

    def check(self, db, uid, passwd):
        try:
            return super(users,self).check(db, uid, passwd)
        except openerp.exceptions.AccessDenied:
            pass

        if not passwd:
            # empty passwords disallowed for obvious security reasons
            raise openerp.exceptions.AccessDenied()

        cr = pooler.get_db(db).cursor()
        user = self.browse(cr, 1, uid)
        logger = logging.getLogger('orm.ldap')
        if user and user.company_id.ldaps:
            for res_company_ldap in user.company_id.ldaps:
                try:
                    l = ldap.open(res_company_ldap.ldap_server, res_company_ldap.ldap_server_port)
                    # An empty binddn means anonymous auth, so it should be replaced w/ an empty string
                    # See LDAP RFC 4513, Section 5.1.1
                    if l.simple_bind_s(res_company_ldap.ldap_binddn or '',
                                       res_company_ldap.ldap_password or ''):
                        base = res_company_ldap.ldap_base
                        scope = ldap.SCOPE_SUBTREE
                        filter = filter_format(res_company_ldap.ldap_filter, (user.login,))
                        retrieve_attributes = None
                        result_id = l.search(base, scope, filter, retrieve_attributes)
                        timeout = 60
                        result_type, result_data = l.result(result_id, timeout)
                        if result_data and result_type == ldap.RES_SEARCH_RESULT and len(result_data) == 1:
                            dn = result_data[0][0]
                            # some LDAP servers allow anonymous binding with blank passwords,
                            # but these have been rejected above, so we're safe to use bind()
                            if l.bind_s(dn, passwd):
                                l.unbind()
                                self._uid_cache.setdefault(db, {})[uid] = passwd
                                cr.close()
                                return True
                        l.unbind()
                except Exception:
                    logger.warning('cannot check', exc_info=True)
                    pass
        cr.close()
        raise openerp.exceptions.AccessDenied()
        
users()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

