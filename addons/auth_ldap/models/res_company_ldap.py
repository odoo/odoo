# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ldap
import logging
from ldap.filter import filter_format

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)


class CompanyLDAP(models.Model):
    _name = 'res.company.ldap'
    _order = 'sequence'
    _rec_name = 'ldap_server'

    sequence = fields.Integer(default=10)
    company = fields.Many2one('res.company', string='Company', required=True, ondelete='cascade')
    ldap_server = fields.Char(string='LDAP Server address', required=True, default='127.0.0.1')
    ldap_server_port = fields.Integer(string='LDAP Server port', required=True, default=389)
    ldap_binddn = fields.Char('LDAP binddn',
        help="The user account on the LDAP server that is used to query the directory. "
             "Leave empty to connect anonymously.")
    ldap_password = fields.Char(string='LDAP password',
        help="The password of the user account on the LDAP server that is used to query the directory.")
    ldap_filter = fields.Char(string='LDAP filter', required=True)
    ldap_base = fields.Char(string='LDAP base', required=True)
    user = fields.Many2one('res.users', string='Template User',
        help="User to copy when creating new users")
    create_user = fields.Boolean(default=True,
        help="Automatically create local user accounts for new users authenticating via LDAP")
    ldap_tls = fields.Boolean(string='Use TLS',
        help="Request secure TLS/SSL encryption when connecting to the LDAP server. "
             "This option requires a server with STARTTLS enabled, "
             "otherwise all authentication attempts will fail.")

    @api.multi
    def get_ldap_dicts(self):
        """
        Retrieve res_company_ldap resources from the database in dictionary
        format.
        :return: ldap configurations
        :rtype: list of dictionaries
        """

        ldaps = self.sudo().search([('ldap_server', '!=', False)], order='sequence')
        res = ldaps.read([
            'id',
            'company',
            'ldap_server',
            'ldap_server_port',
            'ldap_binddn',
            'ldap_password',
            'ldap_filter',
            'ldap_base',
            'user',
            'create_user',
            'ldap_tls'
        ])
        return res

    def connect(self, conf):
        """
        Connect to an LDAP server specified by an ldap
        configuration dictionary.

        :param dict conf: LDAP configuration
        :return: an LDAP object
        """

        uri = 'ldap://%s:%d' % (conf['ldap_server'], conf['ldap_server_port'])

        connection = ldap.initialize(uri)
        if conf['ldap_tls']:
            connection.start_tls_s()
        return connection

    def authenticate(self, conf, login, password):
        """
        Authenticate a user against the specified LDAP server.

        In order to prevent an unintended 'unauthenticated authentication',
        which is an anonymous bind with a valid dn and a blank password,
        check for empty passwords explicitely (:rfc:`4513#section-6.3.1`)
        :param dict conf: LDAP configuration
        :param login: username
        :param password: Password for the LDAP user
        :return: LDAP entry of authenticated user or False
        :rtype: dictionary of attributes
        """

        if not password:
            return False

        entry = False
        try:
            filter = filter_format(conf['ldap_filter'], (login,))
        except TypeError:
            _logger.warning('Could not format LDAP filter. Your filter should contain one \'%s\'.')
            return False
        try:
            results = self.query(conf, tools.ustr(filter))

            # Get rid of (None, attrs) for searchResultReference replies
            results = [i for i in results if i[0]]
            if len(results) == 1:
                dn = results[0][0]
                conn = self.connect(conf)
                conn.simple_bind_s(dn, password.encode('utf-8'))
                conn.unbind()
                entry = results[0]
        except ldap.INVALID_CREDENTIALS:
            return False
        except ldap.LDAPError, e:
            _logger.error('An LDAP exception occurred: %s', e)
        return entry

    def query(self, conf, filter, retrieve_attributes=None):
        """
        Query an LDAP server with the filter argument and scope subtree.

        Allow for all authentication methods of the simple authentication
        method:

        - authenticated bind (non-empty binddn + valid password)
        - anonymous bind (empty binddn + empty password)
        - unauthenticated authentication (non-empty binddn + empty password)

        .. seealso::
           :rfc:`4513#section-5.1` - LDAP: Simple Authentication Method.

        :param dict conf: LDAP configuration
        :param filter: valid LDAP filter
        :param list retrieve_attributes: LDAP attributes to be retrieved. \
        If not specified, return all attributes.
        :return: ldap entries
        :rtype: list of tuples (dn, attrs)

        """

        results = []
        try:
            conn = self.connect(conf)
            ldap_password = conf['ldap_password'] or ''
            ldap_binddn = conf['ldap_binddn'] or ''
            conn.simple_bind_s(ldap_binddn.encode('utf-8'), ldap_password.encode('utf-8'))
            results = conn.search_st(conf['ldap_base'].encode('utf-8'), ldap.SCOPE_SUBTREE, filter, retrieve_attributes, timeout=60)
            conn.unbind()
        except ldap.INVALID_CREDENTIALS:
            _logger.error('LDAP bind failed.')
        except ldap.LDAPError, e:
            _logger.error('An LDAP exception occurred: %s', e)
        return results

    def map_ldap_attributes(self, conf, login, ldap_entry):
        """
        Compose values for a new resource of model res_users,
        based upon the retrieved ldap entry and the LDAP settings.
        :param dict conf: LDAP configuration
        :param login: the new user's login
        :param tuple ldap_entry: single LDAP result (dn, attrs)
        :return: parameters for a new resource of model res_users
        :rtype: dict
        """

        return {
            'name': ldap_entry[1]['cn'][0],
            'login': login,
            'company_id': conf['company'][0]
        }

    @api.model
    def get_or_create_user(self, conf, login, ldap_entry):
        """
        Retrieve an active resource of model res_users with the specified
        login. Create the user if it is not initially found.

        :param dict conf: LDAP configuration
        :param login: the user's login
        :param tuple ldap_entry: single LDAP result (dn, attrs)
        :return: res_users id
        :rtype: int
        """

        user_id = False
        login = tools.ustr(login.lower().strip())
        self.env.cr.execute("SELECT id, active FROM res_users WHERE lower(login)=%s", (login,))
        res = self.env.cr.fetchone()
        if res:
            if res[1]:
                user_id = res[0]
        elif conf['create_user']:
            _logger.debug("Creating new Odoo user \"%s\" from LDAP" % login)
            values = self.map_ldap_attributes(conf, login, ldap_entry)
            SudoUser = self.env['res.users'].sudo().with_context(no_reset_password=True)
            if conf['user']:
                values['active'] = True
                user_id = SudoUser.browse(conf['user'][0]).copy(default=values).id
            else:
                user_id = SudoUser.create(values).id
        return user_id
