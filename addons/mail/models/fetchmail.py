# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import imaplib
import logging
import poplib
import socket

from imaplib import IMAP4, IMAP4_SSL
from poplib import POP3, POP3_SSL
from socket import gaierror, timeout
from ssl import SSLError

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)
MAX_POP_MESSAGES = 50
MAIL_TIMEOUT = 60

# Workaround for Python 2.7.8 bug https://bugs.python.org/issue23906
poplib._MAXLINE = 65536

# Add timeout to IMAP connections
# HACK https://bugs.python.org/issue38615
# TODO: clean in Python 3.9
IMAP4._create_socket = lambda self, timeout=MAIL_TIMEOUT: socket.create_connection((self.host or None, self.port), timeout)


def make_wrap_property(name):
    return property(
        lambda self: getattr(self.__obj__, name),
        lambda self, value: setattr(self.__obj__, name, value),
    )


class IMAP4Connection:
    """Wrapper around IMAP4 and IMAP4_SSL"""
    def __init__(self, server, port, is_ssl):
        self.__obj__ = IMAP4_SSL(server, port) if is_ssl else IMAP4(server, port)


class POP3Connection:
    """Wrapper around POP3 and POP3_SSL"""
    def __init__(self, server, port, is_ssl, timeout=MAIL_TIMEOUT):
        self.__obj__ = POP3_SSL(server, port, timeout=timeout) if is_ssl else POP3(server, port, timeout=timeout)


IMAP_COMMANDS = [cmd.lower() for cmd in imaplib.Commands]
IMAP_ATTRIBUTES = ['examine', 'login_cram_md5', 'move', 'recent', 'response', 'shutdown', 'unselect'] + IMAP_COMMANDS
POP3_ATTRIBUTES = [
    'apop', 'capa', 'close', 'dele', 'list', 'noop', 'pass_', 'quit', 'retr', 'rpop', 'rset', 'set_debuglevel', 'stat',
    'stls', 'top', 'uidl', 'user', 'utf8'
]
for name in IMAP_ATTRIBUTES:
    setattr(IMAP4Connection, name, make_wrap_property(name))

for name in POP3_ATTRIBUTES:
    setattr(POP3Connection, name, make_wrap_property(name))


class FetchmailServer(models.Model):
    """Incoming POP/IMAP mail server account"""

    _name = 'fetchmail.server'
    _description = 'Incoming Mail Server'
    _order = 'priority'

    name = fields.Char('Name', required=True)
    active = fields.Boolean('Active', default=True)
    state = fields.Selection([
        ('draft', 'Not Confirmed'),
        ('done', 'Confirmed'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    server = fields.Char(string='Server Name', readonly=False, help="Hostname or IP of the mail server")
    port = fields.Integer()
    server_type = fields.Selection([
        ('imap', 'IMAP Server'),
        ('pop', 'POP Server'),
        ('local', 'Local Server'),
    ], string='Server Type', index=True, required=True, default='imap')
    server_type_info = fields.Text('Server Type Info', compute='_compute_server_type_info')
    is_ssl = fields.Boolean('SSL/TLS', help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP3S=995)")
    attach = fields.Boolean('Keep Attachments', help="Whether attachments should be downloaded. "
                                                     "If not enabled, incoming emails will be stripped of any attachments before being processed", default=True)
    original = fields.Boolean('Keep Original', help="Whether a full original copy of each email should be kept for reference "
                                                    "and attached to each processed message. This will usually double the size of your message database.")
    date = fields.Datetime(string='Last Fetch Date', readonly=True)
    user = fields.Char(string='Username', readonly=False)
    password = fields.Char()
    object_id = fields.Many2one('ir.model', string="Create a New Record", help="Process each incoming mail as part of a conversation "
                                                                                "corresponding to this document type. This will create "
                                                                                "new documents for new conversations, or attach follow-up "
                                                                                "emails to the existing conversations (documents).")
    priority = fields.Integer(string='Server Priority', readonly=False, help="Defines the order of processing, lower values mean higher priority", default=5)
    message_ids = fields.One2many('mail.mail', 'fetchmail_server_id', string='Messages', readonly=True)
    configuration = fields.Text('Configuration', readonly=True)
    script = fields.Char(readonly=True, default='/mail/static/scripts/odoo-mailgate.py')

    @api.depends('server_type')
    def _compute_server_type_info(self):
        for server in self:
            if server.server_type == 'local':
                server.server_type_info = _('Use a local script to fetch your emails and create new records.')
            else:
                server.server_type_info = False

    @api.onchange('server_type', 'is_ssl', 'object_id')
    def onchange_server_type(self):
        self.port = 0
        if self.server_type == 'pop':
            self.port = self.is_ssl and 995 or 110
        elif self.server_type == 'imap':
            self.port = self.is_ssl and 993 or 143

        conf = {
            'dbname': self.env.cr.dbname,
            'uid': self.env.uid,
            'model': self.object_id.model if self.object_id else 'MODELNAME'
        }
        self.configuration = """Use the below script with the following command line options with your Mail Transport Agent (MTA)
odoo-mailgate.py --host=HOSTNAME --port=PORT -u %(uid)d -p PASSWORD -d %(dbname)s
Example configuration for the postfix mta running locally:
/etc/postfix/virtual_aliases: @youdomain odoo_mailgate@localhost
/etc/aliases:
odoo_mailgate: "|/path/to/odoo-mailgate.py --host=localhost -u %(uid)d -p PASSWORD -d %(dbname)s"
        """ % conf

    @api.model_create_multi
    def create(self, vals_list):
        res = super(FetchmailServer, self).create(vals_list)
        self._update_cron()
        return res

    def write(self, values):
        res = super(FetchmailServer, self).write(values)
        self._update_cron()
        return res

    def unlink(self):
        res = super(FetchmailServer, self).unlink()
        self._update_cron()
        return res

    def set_draft(self):
        self.write({'state': 'draft'})
        return True

    def connect(self, allow_archived=False):
        """
        :param bool allow_archived: by default (False), an exception is raised when calling this method on an
           archived record. It can be set to True for testing so that the exception is no longer raised.
        """
        self.ensure_one()
        if not allow_archived and not self.active:
            raise UserError(_('The server "%s" cannot be used because it is archived.', self.display_name))
        connection_type = self._get_connection_type()
        if connection_type == 'imap':
            connection = IMAP4Connection(self.server, int(self.port), self.is_ssl)
            self._imap_login(connection)
        elif connection_type == 'pop':
            connection = POP3Connection(self.server, int(self.port), self.is_ssl)
            #TODO: use this to remove only unread messages
            #connection.user("recent:"+server.user)
            connection.user(self.user)
            connection.pass_(self.password)
        return connection

    def _imap_login(self, connection):
        """Authenticate the IMAP connection.

        Can be overridden in other module for different authentication methods.

        :param connection: The IMAP connection to authenticate
        """
        self.ensure_one()
        connection.login(self.user, self.password)

    def button_confirm_login(self):
        for server in self:
            connection = None
            try:
                connection = server.connect(allow_archived=True)
                server.write({'state': 'done'})
            except UnicodeError as e:
                raise UserError(_("Invalid server name!\n %s", tools.exception_to_unicode(e)))
            except (gaierror, timeout, IMAP4.abort) as e:
                raise UserError(_("No response received. Check server information.\n %s", tools.exception_to_unicode(e)))
            except (IMAP4.error, poplib.error_proto) as err:
                raise UserError(_("Server replied with following exception:\n %s", tools.exception_to_unicode(err)))
            except SSLError as e:
                raise UserError(_("An SSL exception occurred. Check SSL/TLS configuration on server port.\n %s", tools.exception_to_unicode(e)))
            except (OSError, Exception) as err:
                _logger.info("Failed to connect to %s server %s.", server.server_type, server.name, exc_info=True)
                raise UserError(_("Connection test failed: %s", tools.exception_to_unicode(err)))
            finally:
                try:
                    if connection:
                        connection_type = server._get_connection_type()
                        if connection_type == 'imap':
                            connection.close()
                        elif connection_type == 'pop':
                            connection.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass
        return True

    @api.model
    def _fetch_mails(self):
        """ Method called by cron to fetch mails from servers """
        return self.search([('state', '=', 'done'), ('server_type', '!=', 'local')]).fetch_mail(raise_exception=False)

    def fetch_mail(self, raise_exception=True):
        """ WARNING: meant for cron usage only - will commit() after each email! """
        additionnal_context = {
            'fetchmail_cron_running': True
        }
        MailThread = self.env['mail.thread']
        for server in self:
            _logger.info('start checking for new emails on %s server %s', server.server_type, server.name)
            additionnal_context['default_fetchmail_server_id'] = server.id
            count, failed = 0, 0
            imap_server = None
            pop_server = None
            connection_type = server._get_connection_type()
            if connection_type == 'imap':
                try:
                    imap_server = server.connect()
                    imap_server.select()
                    result, data = imap_server.search(None, '(UNSEEN)')
                    for num in data[0].split():
                        res_id = None
                        result, data = imap_server.fetch(num, '(RFC822)')
                        imap_server.store(num, '-FLAGS', '\\Seen')
                        try:
                            res_id = MailThread.with_context(**additionnal_context).message_process(server.object_id.model, data[0][1], save_original=server.original, strip_attachments=(not server.attach))
                        except Exception:
                            _logger.info('Failed to process mail from %s server %s.', server.server_type, server.name, exc_info=True)
                            failed += 1
                        imap_server.store(num, '+FLAGS', '\\Seen')
                        self._cr.commit()
                        count += 1
                    _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", count, server.server_type, server.name, (count - failed), failed)
                except Exception as e:
                    if raise_exception:
                        raise ValidationError(_("Couldn't get your emails. Check out the error message below for more info:\n%s", e)) from e
                    else:
                        _logger.info("General failure when trying to fetch mail from %s server %s.", server.server_type, server.name, exc_info=True)
                finally:
                    if imap_server:
                        try:
                            imap_server.close()
                            imap_server.logout()
                        except OSError:
                            _logger.warning('Failed to properly finish imap connection: %s.', server.name, exc_info=True)
            elif connection_type == 'pop':
                try:
                    while True:
                        failed_in_loop = 0
                        num = 0
                        pop_server = server.connect()
                        (num_messages, total_size) = pop_server.stat()
                        pop_server.list()
                        for num in range(1, min(MAX_POP_MESSAGES, num_messages) + 1):
                            (header, messages, octets) = pop_server.retr(num)
                            message = (b'\n').join(messages)
                            res_id = None
                            try:
                                res_id = MailThread.with_context(**additionnal_context).message_process(server.object_id.model, message, save_original=server.original, strip_attachments=(not server.attach))
                                pop_server.dele(num)
                            except Exception:
                                _logger.info('Failed to process mail from %s server %s.', server.server_type, server.name, exc_info=True)
                                failed += 1
                                failed_in_loop += 1
                            self.env.cr.commit()
                        _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", num, server.server_type, server.name, (num - failed_in_loop), failed_in_loop)
                        # Stop if (1) no more message left or (2) all messages have failed
                        if num_messages < MAX_POP_MESSAGES or failed_in_loop == num:
                            break
                        pop_server.quit()
                except Exception as e:
                    if raise_exception:
                        raise ValidationError(_("Couldn't get your emails. Check out the error message below for more info:\n%s", e)) from e
                    else:
                        _logger.info("General failure when trying to fetch mail from %s server %s.", server.server_type, server.name, exc_info=True)
                finally:
                    if pop_server:
                        try:
                            pop_server.quit()
                        except OSError:
                            _logger.warning('Failed to properly finish pop connection: %s.', server.name, exc_info=True)
            server.write({'date': fields.Datetime.now()})
        return True

    def _get_connection_type(self):
        """Return which connection must be used for this mail server (IMAP or POP).
        Can be overridden in sub-module to define which connection to use for a specific
        "server_type" (e.g. Gmail server).
        """
        self.ensure_one()
        return self.server_type

    @api.model
    def _update_cron(self):
        if self.env.context.get('fetchmail_cron_running'):
            return
        try:
            # Enabled/Disable cron based on the number of 'done' server of type pop or imap
            cron = self.env.ref('mail.ir_cron_mail_gateway_action')
            cron.toggle(model=self._name, domain=[('state', '=', 'done'), ('server_type', '!=', 'local')])
        except ValueError:
            pass
