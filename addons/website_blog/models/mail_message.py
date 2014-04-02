# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class MailMessage(osv.Model):
    _inherit = 'mail.message'

    _columns = {
        'discussion_key': fields.char('Discussion Key',
            help='Used in Blogs to display messages in a group based on their discussion key.'),
    }
