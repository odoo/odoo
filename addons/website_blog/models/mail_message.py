# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.osv import osv, fields


class MailMessage(osv.Model):
    _inherit = 'mail.message'

    _columns = {
        'path': fields.char(
            'Discussion Path', select=1,
            help='Used to display messages in a paragraph-based chatter using a unique path;'),
    }
