# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (C) P. Christeas, 2009, all rights reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields

class ir_attachment(osv.osv):
    _inherit = 'ir.attachment'

    _columns = {
        'proto_num' : fields.char('Protocol Number', size=32),
	'proto_date': fields.datetime('Protocol Date', readonly=False),
	'proto_from': fields.char('From',size=100, help="A textual description where the document has come from."),
	'proto_to': fields.char('To',size=100,help="The main recepient of this document"),
        'signature_ids': fields.one2many('document.signature', 'file_id', 'Signatures', readonly=True),
    }

    _defaults = {
    }

ir_attachment()

class document_signature(osv.osv):
    """ A detached digital signature for a file
    """
    _name = 'document.signature'
    _columns = {
        'file_id' :fields.many2one('ir.attachment', 'File', readonly=True, required=True),
        'write_uid': fields.many2one('res.users', 'User', readonly=True),
        'write_date': fields.datetime('Date', readonly=True),
        'sig_type' : fields.selection([('gpg','GPG'),('sha','SHA')], 'Type', required=True),
        'signature': fields.text('Signature',required=True),
        'keyid': fields.char('Key ID',size=64,help="The key id used to generate the signature"),
        'status': fields.selection([('valid','Valid'),('invalid','Invalid'),('unknown','Unknown')], 'Status',
                help="Last known status of signature. Do NOT trust this, unless you verify the signature yourself"),
    }

    _defaults = {
        'sig_type': lambda *a: 'gpg',
        'status': lambda *a: 'unknown',
    }

document_signature()

#eof