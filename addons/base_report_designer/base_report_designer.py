##############################################################################
#
# Copyright (c) 2004-2007 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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

from osv import fields,osv
from wizard.tiny_sxw2rml import sxw2rml
from StringIO import StringIO
from report import interface
import base64
import pooler
import tools

class report_xml(osv.osv):
	_inherit = 'ir.actions.report.xml'

	def upload_report(self, cr, uid, report_id, file_sxw, context):
		'''
		Untested function
		'''
		pool = pooler.get_pool(cr.dbname)
		sxwval = StringIO(base64.decodestring(file_sxw))
		fp = tools.file_open('normalized_oo2rml.xsl',
				subdir='addons/base_report_designer/wizard/tiny_sxw2rml')
		file('/tmp/test.sxw','wb').write(base64.decodestring(file_sxw))
		report = pool.get('ir.actions.report.xml').write(cr, uid, [report_id], {
			'report_sxw_content': base64.decodestring(file_sxw),
			'report_rml_content': str(sxw2rml(sxwval, xsl=fp.read()))
		})
		cr.commit()
		db = pooler.get_db_only(cr.dbname)
		print 'Register'
		interface.register_all(db)
		print 'Register End'
		return True
	def report_get(self, cr, uid, report_id, context={}):
		report = self.browse(cr, uid, report_id, context)
		return {
			'report_sxw_content': report.report_sxw_content and base64.encodestring(report.report_sxw_content) or False,
			'report_rml_content': report.report_rml_content and base64.encodestring(report.report_rml_content) or False
		}
report_xml()
