# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class MailMessage(osv.Model):
    _inherit = 'mail.message'

    _columns = {
        'path': fields.char(
            'Discussion Path', select=1,
            help='Used to display messages in a paragraph-based chatter using a unique path;'),
    }
