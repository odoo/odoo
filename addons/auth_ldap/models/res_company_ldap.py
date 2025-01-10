# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ldap
import logging
from ldap.filter import filter_format

from odoo import _, fields, models, tools
from odoo.exceptions import AccessDenied
from odoo.tools.misc import str2bool

_logger = logging.getLogger(__name__)


class LDAPWrapper:
    def __init__(self, obj):
        self.__obj__ = obj

    def passwd_s(self, *args, **kwargs):
        self.__obj__.passwd_s(*args, **kwargs)

    def search_st(self, *args, **kwargs):
        return self.__obj__.search_st(*args, **kwargs)

    def simple_bind_s(self, *args, **kwargs):
        self.__obj__.simple_bind_s(*args, **kwargs)

    def unbind(self, *args, **kwargs):
        self.__obj__.unbind(*args, **kwargs)


class ResCompanyLdap(models.Model):
    _name = 'res.company.ldap'
    _description = 'Company LDAP configuration'
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
    ldap_filter = fields.Char(string='LDAP filter', required=True, help="""\
    Filter used to look up user accounts in the LDAP database. It is an\
    arbitrary LDAP filter in string representation. Any `%s` placeholder\
    will be replaced by the login (identifier) provided by the user, the filter\
    should contain at least one such placeholder.

    The filter must result in exactly one (1) result, otherwise the login will\
    be considered invalid.

    Example (actual attributes depend on LDAP server and setup):

        (&(objectCategory=person)(objectClass=user)(sAMAccountName=%s))

    or

        (|(mail=%s)(uid=%s))
    """)
    ldap_base = fields.Char(string='LDAP base', required=True, help="DN of the user search scope: all descendants of this base will be searched for users.")
    user = fields.Many2one('res.users', string='Template User',
        help="User to copy when creating new users")
    create_user = fields.Boolean(default=True,
        help="Automatically create local user accounts for new users authenticating via LDAP")
    ldap_tls = fields.Boolean(string='Use TLS',
        help="Request secure TLS/SSL encryption when connecting to the LDAP server. "
             "This option requires a server with STARTTLS enabled, "
             "otherwise all authentication attempts will fail.")

    def _get_ldap_dicts(self):
        """
        Retrieve res_company_ldap resources from the database in dictionary
        format.
        :return: ldap configurations
        :rtype: list of dictionaries
        """

        res = self.sudo().search_read([('ldap_server', '!=', False)], [
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
        ], order='sequence')
        return res

    def _connect(self, conf):
        """
        Connect to an LDAP server specified by an ldap
        configuration dictionary.

        :param dict conf: LDAP configuration
        :return: an LDAP object
        """

        uri = 'ldap://%s:%d' % (conf['ldap_server'], conf['ldap_server_port'])

        connection = ldap.initialize(uri)
        ldap_chase_ref_disabled = self.env['ir.config_parameter'].sudo().get_param('auth_ldap.disable_chase_ref', 'True')
        if str2bool(ldap_chase_ref_disabled):
            connection.set_option(ldap.OPT_REFERRALS, ldap.OPT_OFF)
        if conf['ldap_tls']:
            connection.start_tls_s()
        return LDAPWrapper(connection)

    def _get_entry(self, conf, login):
        filter_tmpl = conf['ldap_filter']
        placeholders = filter_tmpl.count('%s')
        if not placeholders:
            _logger.warning("LDAP filter %r contains no placeholder ('%%s').", filter_tmpl)

        formatted_filter = filter_format(filter_tmpl, [login] * placeholders)
        results = self._query(conf, formatted_filter)

        # Get rid of results (dn, attrs) without a dn
        results = [entry for entry in results if entry[0]]

        dn, entry = False, False
        if len(results) == 1:
            dn, _ = entry = results[0]
        return dn, entry

    def _authenticate(self, conf, login, password):
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

        dn, entry = self._get_entry(conf, login)
        if not dn:
            return False
        try:
            conn = self._connect(conf)
            conn.simple_bind_s(dn, password)
            conn.unbind()
        except ldap.INVALID_CREDENTIALS:
            return False
        except ldap.LDAPError as e:
            _logger.error('An LDAP exception occurred: %s', e)
            return False
        return entry

    def _query(self, conf, filter, retrieve_attributes=None):
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
            conn = self._connect(conf)
            ldap_password = conf['ldap_password'] or ''
            ldap_binddn = conf['ldap_binddn'] or ''
            conn.simple_bind_s(ldap_binddn, ldap_password)
            results = conn.search_st(conf['ldap_base'], ldap.SCOPE_SUBTREE, filter, retrieve_attributes, timeout=60)
            conn.unbind()
        except ldap.INVALID_CREDENTIALS:
            _logger.error('LDAP bind failed.')
        except ldap.LDAPError as e:
            _logger.error('An LDAP exception occurred: %s', e)
        return results

    def _map_ldap_attributes(self, conf, login, ldap_entry):
        """
        Compose values for a new resource of model res_users,
        based upon the retrieved ldap entry and the LDAP settings.
        :param dict conf: LDAP configuration
        :param login: the new user's login
        :param tuple ldap_entry: single LDAP result (dn, attrs)
        :return: parameters for a new resource of model res_users
        :rtype: dict
        """
        data = {
            'name': ldap_entry[1]['cn'][0],
            'login': login,
            'company_id': conf['company'][0]
        }
        if tools.single_email_re.match(login):
            data['email'] = login
        return data

    def _get_or_create_user(self, conf, login, ldap_entry):
        """
        Retrieve an active resource of model res_users with the specified
        login. Create the user if it is not initially found.

        :param dict conf: LDAP configuration
        :param login: the user's login
        :param tuple ldap_entry: single LDAP result (dn, attrs)
        :return: res_users id
        :rtype: int
        """
        login = login.lower().strip()
        self.env.cr.execute("SELECT id, active FROM res_users WHERE lower(login)=%s", (login,))
        res = self.env.cr.fetchone()
        if res:
            if res[1]:
                return res[0]
        elif conf['create_user']:
            _logger.debug("Creating new Odoo user \"%s\" from LDAP" % login)
            values = self._map_ldap_attributes(conf, login, ldap_entry)
            SudoUser = self.env['res.users'].sudo().with_context(no_reset_password=True)
            if conf['user']:
                values['active'] = True
                return SudoUser.browse(conf['user'][0]).copy(default=values).id
            else:
                return SudoUser.create(values).id

        raise AccessDenied(_("No local user found for LDAP login and not configured to create one"))

    def _change_password(self, conf, login, old_passwd, new_passwd):
        changed = False
        dn, entry = self._get_entry(conf, login)
        if not dn:
            return False
        try:
            conn = self._connect(conf)
            conn.simple_bind_s(dn, old_passwd)
            conn.passwd_s(dn, old_passwd, new_passwd)
            changed = True
            conn.unbind()
        except ldap.INVALID_CREDENTIALS:
            pass
        except ldap.LDAPError as e:
            _logger.error('An LDAP exception occurred: %s', e)
        return changed

    def test_ldap_connection(self):
        """
        Test the LDAP connection using the current configuration.
        Returns a dictionary with notification parameters indicating success or failure.
        """
        conf = {
            'ldap_server': self.ldap_server,
            'ldap_server_port': self.ldap_server_port,
            'ldap_binddn': self.ldap_binddn,
            'ldap_password': self.ldap_password,
            'ldap_base': self.ldap_base,
            'ldap_tls': self.ldap_tls
        }

        bind_dn = self.ldap_binddn or ''
        bind_passwd = self.ldap_password or ''

        try:
            conn = self._connect(conf)
            conn.simple_bind_s(bind_dn, bind_passwd)
            conn.unbind()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': _('Connection Test Successful!'),
                    'message': _("Successfully connected to LDAP server at %(server)s:%(port)d",
                                 server=self.ldap_server, port=self.ldap_server_port),
                    'sticky': False,
                }
            }

        except ldap.SERVER_DOWN:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': _('Connection Test Failed!'),
                    'message': _("Cannot contact LDAP server at %(server)s:%(port)d",
                                 server=self.ldap_server, port=self.ldap_server_port),
                    'sticky': False,
                }
            }

        except ldap.INVALID_CREDENTIALS:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': _('Connection Test Failed!'),
                    'message': _("Invalid credentials for bind DN %(binddn)s",
                                 binddn=self.ldap_binddn),
                    'sticky': False,
                }
            }

        except ldap.TIMEOUT:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': _('Connection Test Failed!'),
                    'message': _("Connection to LDAP server at %(server)s:%(port)d timed out",
                                 server=self.ldap_server, port=self.ldap_server_port),
                    'sticky': False,
                }
            }

        except ldap.LDAPError as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': _('Connection Test Failed!'),
                    'message': _("An error occurred: %(error)s",
                                 error=e),
                    'sticky': False,
                }
            }