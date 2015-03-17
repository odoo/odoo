# -*- coding: utf-8 -*-

import ldap
import logging
from ldap.filter import filter_format

import openerp.exceptions
from openerp import api, fields, models, SUPERUSER_ID, tools
from openerp.modules.registry import RegistryManager
_logger = logging.getLogger(__name__)

class CompanyLDAP(models.Model):
    _name = 'res.company.ldap'
    _order = 'sequence'
    _rec_name = 'ldap_server'

    def connect(self):
        """ 
        Connect to an LDAP server specified by an res.company.ldap
        recordset.

        :return: an LDAP object
        """

        uri = 'ldap://%s:%d' % (self.ldap_server, self.ldap_server_port)

        connection = ldap.initialize(uri)
        if self.ldap_tls:
            connection.start_tls_s()
        return connection

    def authenticate(self, login, password):
        """
        Authenticate a user against the specified LDAP server.

        In order to prevent an unintended 'unauthenticated authentication',
        which is an anonymous bind with a valid dn and a blank password,
        check for empty passwords explicitely (:rfc:`4513#section-6.3.1`)

        :param login: username
        :param password: Password for the LDAP user
        :return: LDAP entry of authenticated user or False
        :rtype: dictionary of attributes
        """

        if not password:
            return False

        entry = False
        filter = filter_format(self.ldap_filter, (login,))
        try:
            results = self.query(filter)

            # Get rid of (None, attrs) for searchResultReference replies
            results = [i for i in results if i[0]]
            if len(results) == 1:
                dn = results[0][0]
                conn = self.connect()
                conn.simple_bind_s(dn, password.encode('utf-8'))
                conn.unbind()
                entry = results[0]
        except ldap.INVALID_CREDENTIALS:
            return False
        except ldap.LDAPError, e:
            _logger.error('An LDAP exception occurred: %s', e)
        return entry

    def query(self, filter, retrieve_attributes=None):
        """ 
        Query an LDAP server with the filter argument and scope subtree.

        Allow for all authentication methods of the simple authentication
        method:

        - authenticated bind (non-empty binddn + valid password)
        - anonymous bind (empty binddn + empty password)
        - unauthenticated authentication (non-empty binddn + empty password)

        .. seealso::
           :rfc:`4513#section-5.1` - LDAP: Simple Authentication Method.

        :param filter: valid LDAP filter
        :param list retrieve_attributes: LDAP attributes to be retrieved. \
        If not specified, return all attributes.
        :return: ldap entries
        :rtype: list of tuples (dn, attrs)

        """

        results = []
        try:
            conn = self.connect()
            conn.simple_bind_s(self.ldap_binddn or '',
                               self.ldap_password.encode('utf-8') or '')
            results = conn.search_st(self.ldap_base, ldap.SCOPE_SUBTREE,
                                     filter, retrieve_attributes, timeout=60)
            conn.unbind()
        except ldap.INVALID_CREDENTIALS:
            _logger.error('LDAP bind failed.')
        except ldap.LDAPError, e:
            _logger.error('An LDAP exception occurred: %s', e)
        return results

    def map_ldap_attributes(self, login, ldap_entry):
        """
        Compose values for a new resource of model res_users,
        based upon the retrieved ldap entry and the LDAP settings.

        :param login: the new user's login
        :param tuple ldap_entry: single LDAP result (dn, attrs)
        :return: parameters for a new resource of model res_users
        :rtype: dict
        """

        values = { 'name': ldap_entry[1]['cn'][0],
                   'login': login,
                   'company_id': self.company.id
                   }
        return values

    def get_or_create_user(self, login, ldap_entry):
        """
        Retrieve an active resource of model res_users with the specified
        login. Create the user if it is not initially found.

        :param login: the user's login
        :param tuple ldap_entry: single LDAP result (dn, attrs)
        :return: res_users id
        :rtype: int
        """

        user_id = False
        login = tools.ustr(login.lower().strip())
        self.env.cr.execute("SELECT id, active FROM res_users WHERE lower(login)=%s", (login,))
        res = self.env.cr.fetchone()
        if res and res[1]:
            user_id = res[0]
        elif self.create_user:
            _logger.debug("Creating new Odoo user \"%s\" from LDAP" % login)
            values = self.map_ldap_attributes(login, ldap_entry)
            if self.user:
                values['active'] = True
                user_id = self.user.copy(default=values).id
            else:
                user_id = self.env['res.users'].create(values).id
        return user_id

    sequence = fields.Integer(default=10)
    company = fields.Many2one('res.company', required=True, ondelete='cascade')
    ldap_server = fields.Char(string='LDAP Server address', required=True, default='127.0.0.1')
    ldap_server_port = fields.Integer(string='LDAP Server port', required=True, default=389)
    ldap_binddn = fields.Char('LDAP binddn',
        help=("The user account on the LDAP server that is used to query "
              "the directory. Leave empty to connect anonymously."))
    ldap_password = fields.Char(string='LDAP password',
        help=("The password of the user account on the LDAP server that is "
              "used to query the directory."))
    ldap_filter = fields.Char(string='LDAP filter', required=True)
    ldap_base = fields.Char(string='LDAP base', required=True)
    user = fields.Many2one('res.users', string='Template User', help="User to copy when creating new users")
    create_user = fields.Boolean(default=True,
        help="Automatically create local user accounts for new users authenticating via LDAP")
    ldap_tls = fields.Boolean(string='Use TLS',
        help="Request secure TLS/SSL encryption when connecting to the LDAP server. "
             "This option requires a server with STARTTLS enabled, "
             "otherwise all authentication attempts will fail.")


class ResCompany(models.Model):
    _inherit = "res.company"

    ldaps = fields.One2many('res.company.ldap', 'company', string='LDAP Parameters', copy=True, groups="base.group_system")


class Users(models.Model):
    _inherit = "res.users"

    def _login(self, db, login, password):
        user_id = super(Users, self)._login(db, login, password)
        if user_id:
            return user_id
        registry = RegistryManager.get(db)
        with registry.cursor() as cr:
            cr.execute("SELECT id FROM res_users WHERE lower(login)=%s", (login,))
            res = cr.fetchone()
            if res:
                return False
            env = openerp.api.Environment(cr, SUPERUSER_ID, {})
            Ldap = env['res.company.ldap']
            for ldap_conf in Ldap.search([('ldap_server', '!=', False)], order='sequence'):
                entry = ldap_conf.authenticate(login, password)
                if entry:
                    user_id = ldap_conf.get_or_create_user(login, entry)
                    if user_id:
                        break
            return user_id

    @api.model
    def check_credentials(self, password):
        try:
            super(Users, self).check_credentials(password)
        except openerp.exceptions.AccessDenied:

            if self.env.user.active:
                Ldap = self.env['res.company.ldap'].sudo()
                for ldap_conf in Ldap.search([('ldap_server', '!=', False)], order='sequence'):
                    if ldap_conf.authenticate(self.env.user.login, password):
                        return
            raise
