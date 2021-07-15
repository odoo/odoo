# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import poplib
from ssl import SSLError
from socket import gaierror, timeout
from imaplib import IMAP4, IMAP4_SSL
from poplib import POP3, POP3_SSL

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)
MAX_POP_MESSAGES = 50
MAIL_TIMEOUT = 60

# Workaround for Python 2.7.8 bug https://bugs.python.org/issue23906
poplib._MAXLINE = 65536


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
    server = fields.Char(string='Server Name', readonly=True, help="Hostname or IP of the mail server", states={'draft': [('readonly', False)]})
    port = fields.Integer(readonly=True, states={'draft': [('readonly', False)]})
    server_type = fields.Selection([
        ('pop', 'POP Server'),
        ('imap', 'IMAP Server'),
        ('local', 'Local Server'),
    ], string='Server Type', index=True, required=True, default='pop')
    is_ssl = fields.Boolean('SSL/TLS', help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP3S=995)")
    attach = fields.Boolean('Keep Attachments', help="Whether attachments should be downloaded. "
                                                     "If not enabled, incoming emails will be stripped of any attachments before being processed", default=True)
    original = fields.Boolean('Keep Original', help="Whether a full original copy of each email should be kept for reference "
                                                    "and attached to each processed message. This will usually double the size of your message database.")
    date = fields.Datetime(string='Last Fetch Date', readonly=True)
    user = fields.Char(string='Username', readonly=True, states={'draft': [('readonly', False)]})
    password = fields.Char(readonly=True, states={'draft': [('readonly', False)]})
    object_id = fields.Many2one('ir.model', string="Create a New Record", help="Process each incoming mail as part of a conversation "
                                                                                "corresponding to this document type. This will create "
                                                                                "new documents for new conversations, or attach follow-up "
                                                                                "emails to the existing conversations (documents).")
    priority = fields.Integer(string='Server Priority', readonly=True, states={'draft': [('readonly', False)]}, help="Defines the order of processing, lower values mean higher priority", default=5)
    message_ids = fields.One2many('mail.mail', 'fetchmail_server_id', string='Messages', readonly=True)
    configuration = fields.Text('Configuration', readonly=True)
    script = fields.Char(readonly=True, default='/mail/static/scripts/odoo-mailgate.py')

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

    @api.model
    def create(self, values):
        res = super(FetchmailServer, self).create(values)
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

    def connect(self):
        self.ensure_one()
        if self.server_type == 'imap':
            if self.is_ssl:
                connection = IMAP4_SSL(self.server, int(self.port))
            else:
                connection = IMAP4(self.server, int(self.port))
            connection.login(self.user, self.password)
        elif self.server_type == 'pop':
            if self.is_ssl:
                connection = POP3_SSL(self.server, int(self.port))
            else:
                connection = POP3(self.server, int(self.port))
            #TODO: use this to remove only unread messages
            #connection.user("recent:"+server.user)
            connection.user(self.user)
            connection.pass_(self.password)
        # Add timeout on socket
        connection.sock.settimeout(MAIL_TIMEOUT)
        return connection

    def button_confirm_login(self):
        for server in self:
            try:
                connection = server.connect()
                server.write({'state': 'done'})
            except UnicodeError as e:
                raise UserError(_("Invalid server name !\n %s", tools.ustr(e)))
            except (gaierror, timeout, IMAP4.abort) as e:
                raise UserError(_("No response received. Check server information.\n %s", tools.ustr(e)))
            except (IMAP4.error, poplib.error_proto) as err:
                raise UserError(_("Server replied with following exception:\n %s", tools.ustr(err)))
            except SSLError as e:
                raise UserError(_("An SSL exception occurred. Check SSL/TLS configuration on server port.\n %s", tools.ustr(e)))
            except (OSError, Exception) as err:
                _logger.info("Failed to connect to %s server %s.", server.server_type, server.name, exc_info=True)
                raise UserError(_("Connection test failed: %s", tools.ustr(err)))
            finally:
                try:
                    if connection:
                        if server.server_type == 'imap':
                            connection.close()
                        elif server.server_type == 'pop':
                            connection.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass
        return True

    @api.model
    def _fetch_mails(self):
        """ Method called by cron to fetch mails from servers """
        return self.search([('state', '=', 'done'), ('server_type', 'in', ['pop', 'imap'])]).fetch_mail()

    def fetch_mail(self):
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
            if server.server_type == 'imap':
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
                except Exception:
                    _logger.info("General failure when trying to fetch mail from %s server %s.", server.server_type, server.name, exc_info=True)
                finally:
                    if imap_server:
                        imap_server.close()
                        imap_server.logout()
            elif server.server_type == 'pop':
                try:
                    while True:
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
                            self.env.cr.commit()
                        if num_messages < MAX_POP_MESSAGES:
                            break
                        pop_server.quit()
                        _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", num_messages, server.server_type, server.name, (num_messages - failed), failed)
                except Exception:
                    _logger.info("General failure when trying to fetch mail from %s server %s.", server.server_type, server.name, exc_info=True)
                finally:
                    if pop_server:
                        pop_server.quit()
            server.write({'date': fields.Datetime.now()})
        return True

    @api.model
    def _update_cron(self):
        if self.env.context.get('fetchmail_cron_running'):
            return
        try:
            # Enabled/Disable cron based on the number of 'done' server of type pop or imap
            cron = self.env.ref('fetchmail.ir_cron_mail_gateway_action')
            cron.toggle(model=self._name, domain=[('state', '=', 'done'), ('server_type', 'in', ['pop', 'imap'])])
        except ValueError:
            pass
