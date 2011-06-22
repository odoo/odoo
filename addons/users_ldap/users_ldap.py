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

import ldap
from ldap.filter import filter_format
from osv import fields, osv
import pooler
import tools
import logging
from service import security

class CompanyLDAP(osv.osv):
    _name = 'res.company.ldap'
    _order = 'sequence'
    _rec_name = 'ldap_server'

    def get_ldap_dicts(self, cr, ids=None):
        """ 
        Return res_company_ldap resources in the database as a list of
        dictionaries.

        @param cr : database cursor
        @param ids : optional list of res_company_ldap ids
        """

        if ids:
            id_clause = 'AND id IN (%s)'
            args = [tuple(ids)]
        else:
            id_clause = ''
            args = []
        cr.execute("""
            SELECT id, company, ldap_server, ldap_server_port, ldap_binddn,
                   ldap_password, ldap_filter, ldap_base, "user", create_user
            FROM res_company_ldap
            WHERE ldap_server != '' """ + id_clause + """ ORDER BY sequence
        """, args)
        return cr.dictfetchall()

    def connect(self, conf):
        """ 
        Compose an LDAP uri from an ldap configuration dictionary
        and return a connection to it.

        @param conf : LDAP configuration dictionary
        """

        uri = 'ldap://%s:%d' % (conf['ldap_server'],
                                conf['ldap_server_port'])
        return ldap.initialize(uri)

    def authenticate(self, conf, dn, password):
        """
        Perform an atomic LDAP authentication.
        
        @param conf : LDAP configuration dictionary
        @param dn : LDAP dn
        @param password : Password for the LDAP user
        """

        conn = self.connect(conf)
        conn.simple_bind_s(dn, password)
        conn.unbind()
        
    def query(self, conf, filter, retrieve_attributes=None):
        """ 
        Query an LDAP server with the filter argument and scope subtree.
        Return the results in native python-ldap format, ie. a list of
        tuples (dn, attrs).

        @param conf : LDAP configuration dictionary
        @param filter : valid LDAP filter
        @param retrieve_attributes : optional list of LDAP attributes to be
              retrieved. If not specified, return all attributes.
        """

        results = []
        logger = logging.getLogger('orm.ldap')
        try:
            conn = self.connect(conf)
            conn.simple_bind_s(conf['ldap_binddn'] or '',
                               conf['ldap_password'] or '')
            results = conn.search_st(conf['ldap_base'], ldap.SCOPE_SUBTREE,
                                     filter, retrieve_attributes, timeout=60)
            conn.unbind()
        except ldap.LDAPError, e:
            logger.warning('An LDAP exception occurred: %s' % e)
            pass
        return results

    def map_ldap_attributes(self, cr, uid, login, conf, ldap_entry):
        """
        Compose a list of field values for creating a new resource of model
        res_users, based upon the retrieved ldap entry and the LDAP settings.
        
        @param cr : the database cursor
        @param uid : the OpenERP user id
        @param login : the new user's login
        @param conf : LDAP configuration dictionary
        @param ldap_entry : single LDAP result in (dn, attrs) format
        """

        values = { 'name': ldap_entry[1]['cn'][0],
                   'login': login,
                   'company_id': conf['company']
                   }
        if not conf['user']:
            action_obj = self.pool.get('ir.actions.actions')
            values['action_id'] = values['menu_id'] = action_obj.search(
                cr, uid, [('usage', '=', 'menu')], order='id')[0]
        return values
    
    def get_or_create_user(self, cr, uid, login, conf, ldap_entry,
                           context=None):
        """
        Return the id of an active res_users resource with the specified
        login. Create the user if it is not initially found.

        @param cr : the database cursor
        @param uid : the OpenERP user id
        @param login : the user's login
        @param conf : LDAP configuration dictionary
        @param ldap_entry : single LDAP result in (dn, attrs) format
        @param context : the OpenERP context
        """
        
        user_id = False
        login = tools.ustr(login)
        cr.execute("SELECT id, active FROM res_users WHERE login=%s", (login,))
        res = cr.fetchone()
        if res:
            if res[1]:
                user_id = res[0]
        elif conf['create_user']:
            logger = logging.getLogger('orm.ldap')
            logger.debug("Creating new OpenERP user \"%s\" from LDAP" % login)
            user_obj = self.pool.get('res.users')
            values = self.map_ldap_attributes(cr, uid, login, conf, ldap_entry)
            if conf['user']:
                user_id = user_obj.copy(cr, 1, conf['user'],
                                        default={'active': True})
                user_obj.write(cr, 1, user_id, values)
            else:
                user_id = user_obj.create(cr, 1, values)
        return user_id

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
        'ldap_filter': fields.char('LDAP filter', size=64, required=True),
        'ldap_base': fields.char('LDAP base', size=64, required=True),
        'user': fields.many2one('res.users', 'Model User',
            help="Model used for user creation"),
        'create_user': fields.boolean('Create user',
            help="Create the user if not in database"),
    }
    _defaults = {
        'ldap_server': '127.0.0.1',
        'ldap_server_port': 389,
        'sequence': 10,
        'create_user': True,
    }

CompanyLDAP()


class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'ldaps': fields.one2many(
            'res.company.ldap', 'company', 'LDAP Parameters'),
    }
res_company()


class users(osv.osv):
    _inherit = "res.users"
    def login(self, db, login, password):
        user_id = super(users, self).login(db, login, password)
        if user_id:
            return user_id
        cr = pooler.get_db(db).cursor()
        ldap_obj = pooler.get_pool(db).get('res.company.ldap')
        for conf in ldap_obj.get_ldap_dicts(cr):
            filter = filter_format(conf['ldap_filter'], (login,))
            results = ldap_obj.query(conf, filter)
            if results and len(results) == 1:
                entry = results[0]
                dn = entry[0]
                name = entry[1]['cn'][0]
                try:
                    ldap_obj.authenticate(conf, dn, password)
                    user_id = ldap_obj.get_or_create_user(
                        cr, 1, login, conf, entry)
                    if user_id:
                        cr.execute('UPDATE res_users SET date=now() WHERE '
                                   'login=%s', (tools.ustr(login),))
                        cr.commit()
                    break
                except ldap.INVALID_CREDENTIALS:
                    pass
                except ldap.LDAPError, e:
                    logger = logging.getLogger('orm.ldap')
                    logger.warning('An LDAP exception occurred: %s' % e)
                    pass
        cr.close()
        return user_id

    def check(self, db, uid, passwd):
        try:
            return super(users,self).check(db, uid, passwd)
        except security.ExceptionNoTb: # AccessDenied
            pass

        if not passwd:
            # empty passwords disallowed for obvious security reasons
            raise security.ExceptionNoTb('AccessDenied')

        cr = pooler.get_db(db).cursor()
        cr.execute('SELECT login FROM res_users WHERE id=%s AND active=TRUE',
                   (int(uid),))
        res = cr.fetchone()
        if res:
            ldap_obj = pooler.get_pool(db).get('res.company.ldap')
            for conf in ldap_obj.get_ldap_dicts(cr):
                filter = filter_format(conf['ldap_filter'], (res[0],))
                results = ldap_obj.query(conf, filter)
                if results and len(results) == 1:
                    dn = results[0][0]
                    # some LDAP servers allow anonymous binding with blank passwords,
                    # but these have been rejected above, so we're safe to use bind()
                    try:
                        ldap_obj.authenticate(conf, dn, passwd)
                        self._uid_cache.setdefault(db, {})[uid] = passwd
                        cr.close()
                        return True
                    except ldap.LDAPError, e:
                        logger = logging.getLogger('orm.ldap')
                        logger.warning('An LDAP exception occurred: %s' % e)
                        pass
        cr.close()
        raise security.ExceptionNoTb('AccessDenied')
        
users()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
