##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: ir_ui_menu.py 1005 2005-07-25 08:41:42Z nicoe $
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

from osv import fields, osv
from osv.orm import browse_null, browse_record

def one_in(setA, setB):
	"""Check the presence of an element of setA in setB
	"""
	for x in setA:
		if x in setB:
			return True
	return False

icons = map(lambda x: (x,x), ['STOCK_ABOUT', 'STOCK_ADD', 'STOCK_APPLY', 'STOCK_BOLD',
'STOCK_CANCEL', 'STOCK_CDROM', 'STOCK_CLEAR', 'STOCK_CLOSE', 'STOCK_COLOR_PICKER',
'STOCK_CONNECT', 'STOCK_CONVERT', 'STOCK_COPY', 'STOCK_CUT', 'STOCK_DELETE',
'STOCK_DIALOG_AUTHENTICATION', 'STOCK_DIALOG_ERROR', 'STOCK_DIALOG_INFO',
'STOCK_DIALOG_QUESTION', 'STOCK_DIALOG_WARNING', 'STOCK_DIRECTORY', 'STOCK_DISCONNECT',
'STOCK_DND', 'STOCK_DND_MULTIPLE', 'STOCK_EDIT', 'STOCK_EXECUTE', 'STOCK_FILE',
'STOCK_FIND', 'STOCK_FIND_AND_REPLACE', 'STOCK_FLOPPY', 'STOCK_GOTO_BOTTOM',
'STOCK_GOTO_FIRST', 'STOCK_GOTO_LAST', 'STOCK_GOTO_TOP', 'STOCK_GO_BACK',
'STOCK_GO_DOWN', 'STOCK_GO_FORWARD', 'STOCK_GO_UP', 'STOCK_HARDDISK',
'STOCK_HELP', 'STOCK_HOME', 'STOCK_INDENT', 'STOCK_INDEX', 'STOCK_ITALIC',
'STOCK_JUMP_TO', 'STOCK_JUSTIFY_CENTER', 'STOCK_JUSTIFY_FILL',
'STOCK_JUSTIFY_LEFT', 'STOCK_JUSTIFY_RIGHT', 'STOCK_MEDIA_FORWARD',
'STOCK_MEDIA_NEXT', 'STOCK_MEDIA_PAUSE', 'STOCK_MEDIA_PLAY',
'STOCK_MEDIA_PREVIOUS', 'STOCK_MEDIA_RECORD', 'STOCK_MEDIA_REWIND',
'STOCK_MEDIA_STOP', 'STOCK_MISSING_IMAGE', 'STOCK_NETWORK', 'STOCK_NEW',
'STOCK_NO', 'STOCK_OK', 'STOCK_OPEN', 'STOCK_PASTE', 'STOCK_PREFERENCES',
'STOCK_PRINT', 'STOCK_PRINT_PREVIEW', 'STOCK_PROPERTIES', 'STOCK_QUIT',
'STOCK_REDO', 'STOCK_REFRESH', 'STOCK_REMOVE', 'STOCK_REVERT_TO_SAVED',
'STOCK_SAVE', 'STOCK_SAVE_AS', 'STOCK_SELECT_COLOR', 'STOCK_SELECT_FONT',
'STOCK_SORT_ASCENDING', 'STOCK_SORT_DESCENDING', 'STOCK_SPELL_CHECK',
'STOCK_STOP', 'STOCK_STRIKETHROUGH', 'STOCK_UNDELETE', 'STOCK_UNDERLINE',
'STOCK_UNDO', 'STOCK_UNINDENT', 'STOCK_YES', 'STOCK_ZOOM_100',
'STOCK_ZOOM_FIT', 'STOCK_ZOOM_IN', 'STOCK_ZOOM_OUT',
'terp-account', 'terp-crm', 'terp-mrp', 'terp-product', 'terp-purchase', 'terp-sale', 'terp-tools',
'terp-administration', 'terp-hr', 'terp-partner', 'terp-project', 'terp-report', 'terp-stock'
])


class ir_ui_menu(osv.osv):
	_name = 'ir.ui.menu'
	def search(self, cr, uid, args, offset=0, limit=2000, order=None):
		ids = osv.orm.orm.search(self, cr, uid, args, offset, limit, order)
		user_groups = self.pool.get('res.users').read(cr, uid, [uid])[0]['groups_id']
		result = []
		for menu in self.browse(cr, uid, ids):
			if not len(menu.groups_id):
				result.append(menu.id)
				continue
			for g in menu.groups_id:
				if g.id in user_groups:
					result.append(menu.id)
					break
		return result

	def _get_full_name(self, cr, uid, ids, name, args, context):
 		res = {}
		for m in self.browse(cr, uid, ids):
			res[m.id] = self._get_one_full_name(m)
		return res

	def _get_one_full_name(self, menu, level=6):
		if level<=0:
			return '...'
		if menu.parent_id:
			parent_path = self._get_one_full_name(menu.parent_id, level-1) + "/"
		else:
			parent_path = ''
		return parent_path + menu.name

	def copy(self, cr, uid, id, default=None, context={}):
		res = super(ir_ui_menu, self).copy(cr, uid, id, context=context)
		ids = self.pool.get('ir.values').search(cr, uid, [('model','=','ir.ui.menu'),('res_id','=',id)])
		for iv in self.pool.get('ir.values').browse(cr, uid, ids):
			new_id = self.pool.get('ir.values').copy(cr, uid, iv.id, default={'res_id':res}, context=context)
		return res

	_columns = {
		'name': fields.char('Menu', size=64, required=True, translate=True),
		'sequence': fields.integer('Sequence'),
		'child_id' : fields.one2many('ir.ui.menu', 'parent_id','Child ids'),
		'parent_id': fields.many2one('ir.ui.menu', 'Parent Menu', select=True),
		'groups_id': fields.many2many('res.groups', 'ir_ui_menu_group_rel', 'menu_id', 'gid', 'Groups'),
		'complete_name': fields.function(_get_full_name, method=True, string='Complete Name', type='char', size=128),
		'icon': fields.selection(lambda *a: icons, 'Icon', size=64)
	}
	_defaults = {
		'icon' : lambda *a: 'STOCK_OPEN',
		'sequence' : lambda *a: 10
	}
	_order = "sequence,id"
ir_ui_menu()


