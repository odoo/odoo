##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
#
# $Id: letter.py 1304 2005-09-08 14:35:42Z nicoe $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields,osv, orm
import time
import tools
import pooler


class letter_paragraph_type(osv.osv):
	_name = "letter.paragraph.type"
	_columns = {
		'name': fields.char('Paragraph Type', size=60, required=True),
		'sequence': fields.integer('Sequence', required=True),
	}
letter_paragraph_type()

class letter_paragraph(osv.osv):
	_name = "letter.paragraph"
	_columns = {
		'name': fields.char('Paragraph Name', size=60, required=True),
		'sequence': fields.integer('Sequence'),
		'type_id': fields.many2one('letter.paragraph.type', 'Paragraph Type'),
		'content': fields.text('Content'),
	}
letter_paragraph()

class letter_letter_type(osv.osv):
	_name = "letter.letter.type"
	_columns = {
		'name': fields.char('Name', size=60, required=True),
		'template': fields.selection([('default','Default Template')], 'Template', required=True),
		'paragraph_ids': fields.many2many('letter.paragraph', 'letter_letter_paragraph_rel', 'letter_id','paragraph_id', 'Defaults Paragraphs')
	}
letter_letter_type()

class letter_letter(osv.osv):
	_name = "letter.letter"
	_columns = {
		'name': fields.char('Name', size=60, required=True),
		'partner_id': fields.many2one('res.partner', 'Partner', required=True),
		'type_id': fields.many2one('letter.letter.type', 'Letter Type', required=True),
		'state': fields.selection([('draft', 'Draft'),('confirmed','Confirmed')], 'State', required=True),
		'paragraph_ids': fields.one2many('letter.letter.paragraph','letter_id', 'Letter')
	}
	_defaults = {
		'state': lambda *a: 'draft',
	}

	def onchange_type_id(self, cr, uid, ids, type_id):
		if type_id:
			letter = pooler.get_pool(cr.dbname).get('letter.letter.type').browse(cr, uid, type_id)
			return {'value':{'paragraph_ids': [x.id for x in letter.paragraph_ids]}}
		else:
			return  {'value':{'paragraph_ids': []}}

letter_letter()

class letter_letter_paragraph(osv.osv):
	_name = "letter.letter.paragraph"
	_columns = {
		'sequence': fields.integer('Sequence'),
		'name': fields.char('Paragraph Name', size=60, required=True),
		'letter_id': fields.many2one('letter.letter', 'Letter'),
		'type_id': fields.many2one('letter.paragraph.type', 'Paragraph Type'),
		'content': fields.text('Content'),
	}
letter_letter_paragraph()


