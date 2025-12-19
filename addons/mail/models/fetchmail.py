# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import functools
import logging
import poplib

from imaplib import IMAP4, IMAP4_SSL
from poplib import POP3, POP3_SSL
from socket import gaierror, timeout
from ssl import SSLError

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import exception_to_unicode

_logger = logging.getLogger(__name__)
MAIL_TIMEOUT = 60
MAIL_SERVER_DOMAIN = Domain('state', '=', 'done') & Domain('server_type', '!=', 'local')
MAIL_SERVER_DEACTIVATE_TIME = datetime.timedelta(days=5)  # deactivate cron when has general connection issues

# Workaround for Python 2.7.8 bug https://bugs.python.org/issue23906
poplib._MAXLINE = 65536


class OdooIMAP4(IMAP4):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._unread_messages = None

    def check_unread_messages(self):
        self.select()
        _result, data = self.search(None, '(UNSEEN)')
        self._unread_messages = data[0].split() if data and data[0] else []
        self._unread_messages.reverse()
        return len(self._unread_messages)

    def retrieve_unread_messages(self):
        assert self._unread_messages is not None
        while self._unread_messages:
            num = self._unread_messages.pop()
            _result, data = self.fetch(num, '(RFC822)')
            self.store(num, '-FLAGS', '\\Seen')
            yield num, data[0][1]

    def handled_message(self, num):
        self.store(num, '+FLAGS', '\\Seen')

    def disconnect(self):
        if self._unread_messages is not None:
            self.close()
        self.logout()


class OdooIMAP4_SSL(OdooIMAP4, IMAP4_SSL):
    pass


class OdooPOP3(POP3):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._unread_messages = None

    def check_unread_messages(self):
        (num_messages, _total_size) = self.stat()
        self.list()
        self._unread_messages = list(range(num_messages, 0, -1))
        return num_messages

    def retrieve_unread_messages(self):
        while self._unread_messages:
            num = self._unread_messages.pop()
            (_header, messages, _octets) = self.retr(num)
            message = (b'\n').join(messages)
            yield num, message

    def handled_message(self, num):
        self.dele(num)

    def disconnect(self):
        self.quit()


class OdooPOP3_SSL(OdooPOP3, POP3_SSL):
    pass


class FetchmailServer(models.Model):
    """Incoming POP/IMAP mail server account"""
    _name = 'fetchmail.server'
    _description = 'Incoming Mail Server'
    _order = 'priority'
    _email_field = 'user'

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
    error_date = fields.Datetime(string='Last Error Date', readonly=True,
        help="Date of last failure, reset on success.")
    error_message = fields.Text(string='Last Error Message', readonly=True)
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
        res = super().create(vals_list)
        self._update_cron()
        return res

    def write(self, vals):
        res = super().write(vals)
        self._update_cron()
        return res

    def unlink(self):
        res = super().unlink()
        self._update_cron()
        return res

    def set_draft(self):
        self.write({'state': 'draft'})
        return True

    def _connect__(self, allow_archived=False):  # noqa: PLW3201
        """
        :param bool allow_archived: by default (False), an exception is raised when calling this method on an
           archived record. It can be set to True for testing so that the exception is no longer raised.
        """
        self.ensure_one()
        if not allow_archived and not self.active:
            raise UserError(_('The server "%s" cannot be used because it is archived.', self.display_name))
        connection_type = self._get_connection_type()
        if connection_type == 'imap':
            server, port, is_ssl = self.server, int(self.port), self.is_ssl
            connection = OdooIMAP4_SSL(server, port, timeout=MAIL_TIMEOUT) if is_ssl else OdooIMAP4(server, port, timeout=MAIL_TIMEOUT)
            self._imap_login__(connection)
        elif connection_type == 'pop':
            server, port, is_ssl = self.server, int(self.port), self.is_ssl
            connection = OdooPOP3_SSL(server, port, timeout=MAIL_TIMEOUT) if is_ssl else OdooPOP3(server, port, timeout=MAIL_TIMEOUT)
            #TODO: use this to remove only unread messages
            #connection.user("recent:"+server.user)
            connection.user(self.user)
            connection.pass_(self.password)
        return connection

    def _imap_login__(self, connection):  # noqa: PLW3201
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
                connection = server._connect__(allow_archived=True)
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
                        connection.disconnect()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass
        return True

    def fetch_mail(self):
        """ Action to fetch the mail from the current server. """
        self.ensure_one().check_access('write')
        exception = self.sudo()._fetch_mail()
        if exception is not None:
            raise exception

    @api.model
    def _fetch_mails(self, **kw):
        """ Method called by cron to fetch mails from servers """
        assert self.env.context.get('cron_id') == self.env.ref('mail.ir_cron_mail_gateway_action').id, "Meant for cron usage only"
        self.search(MAIL_SERVER_DOMAIN)._fetch_mail(**kw)
        if not self.search_count(MAIL_SERVER_DOMAIN):
            # no server is active anymore
            self.env['ir.cron']._commit_progress(deactivate=True)

    def _fetch_mail(self, batch_limit=50) -> Exception | None:
        """ Fetch e-mails from multiple servers.

        Commit after each message.
        """
        result_exception = None
        servers = self.with_context(fetchmail_cron_running=True)
        total_remaining = len(servers)  # number of remaining messages + number of unchecked servers
        self.env['ir.cron']._commit_progress(remaining=total_remaining)

        for server in servers:
            total_remaining -= 1  # the server is checked
            if not server.try_lock_for_update(allow_referencing=True).filtered_domain(MAIL_SERVER_DOMAIN):
                _logger.info('Skip checking for new mails on mail server id %d (unavailable)', server.id)
                continue
            server_type_and_name = server.server_type, server.name  # avoid reading this after each commit
            _logger.info('Start checking for new emails on %s server %s', *server_type_and_name)
            count, failed = 0, 0

            # processing messages in a separate transaction to keep lock on the server
            server_connection = None
            message_cr = None
            try:
                server_connection = server._connect__()
                message_cr = self.env.registry.cursor()
                MailThread = server.env['mail.thread'].with_env(self.env(cr=message_cr)).with_context(default_fetchmail_server_id=server.id)
                thread_process_message = functools.partial(
                    MailThread.message_process,
                    model=server.object_id.model,
                    save_original=server.original,
                    strip_attachments=(not server.attach),
                )
                unread_message_count = server_connection.check_unread_messages()
                _logger.debug('%d unread messages on %s server %s.', unread_message_count, *server_type_and_name)
                total_remaining += unread_message_count
                for message_num, message in server_connection.retrieve_unread_messages():
                    _logger.debug('Fetched message %r on %s server %s.', message_num, *server_type_and_name)
                    count += 1
                    total_remaining -= 1
                    try:
                        thread_process_message(message=message)
                        remaining_time = MailThread.env['ir.cron']._commit_progress(1)
                    except Exception:  # noqa: BLE001
                        MailThread.env.cr.rollback()
                        failed += 1
                        _logger.info('Failed to process mail from %s server %s.', *server_type_and_name, exc_info=True)
                        remaining_time = MailThread.env['ir.cron']._commit_progress()
                    server_connection.handled_message(message_num)
                    if count >= batch_limit or not remaining_time:
                        break
                server.error_date = False
                server.error_message = False
            except Exception as e:  # noqa: BLE001
                result_exception = e
                _logger.info("General failure when trying to fetch mail from %s server %s.", *server_type_and_name, exc_info=True)
                if not server.error_date:
                    server.error_date = fields.Datetime.now()
                    server.error_message = exception_to_unicode(e)
                elif server.error_date < fields.Datetime.now() - MAIL_SERVER_DEACTIVATE_TIME:
                    message = "Deactivating fetchmail %s server %s (too many failures)" % server_type_and_name
                    server.set_draft()
                    server.env['ir.cron']._notify_admin(message)
            finally:
                if message_cr is not None:
                    message_cr.close()
                try:
                    if server_connection:
                        server_connection.disconnect()
                except (OSError, IMAP4.abort):
                    _logger.warning('Failed to properly finish %s connection: %s.', *server_type_and_name, exc_info=True)
            _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", count, *server_type_and_name, (count - failed), failed)
            server.write({'date': fields.Datetime.now()})
            # Commit before updating the progress because progress may be
            # updated for messages using another transaction. Without a commit
            # before updating the progress, we would have a serialization error.
            self.env.cr.commit()
            if not self.env['ir.cron']._commit_progress(remaining=total_remaining):
                break
        return result_exception

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
            cron.toggle(model=self._name, domain=MAIL_SERVER_DOMAIN)
        except ValueError:
            pass
