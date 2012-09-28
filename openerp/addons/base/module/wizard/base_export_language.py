# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2004-2012 OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import tools
import base64
import cStringIO
from osv import fields,osv
from tools.translate import _
from tools.misc import get_iso_codes

NEW_LANG_KEY = '__new__'

class base_language_export(osv.osv_memory):
    _name = "base.language.export"

    def _get_languages(self, cr, uid, context):
        lang_obj = self.pool.get('res.lang')
        ids = lang_obj.search(cr, uid, [('translatable', '=', True)])
        langs = lang_obj.browse(cr, uid, ids)
        return [(NEW_LANG_KEY, _('New Language (Empty translation template)'))] + [(lang.code, lang.name) for lang in langs]
   
    _columns = {
            'name': fields.char('File Name', readonly=True),
            'lang': fields.selection(_get_languages, 'Language', required=True), 
            'format': fields.selection([('csv','CSV File'),
                                        ('po','PO File'),
                                        ('tgz', 'TGZ Archive')], 'File Format', required=True),
            'modules': fields.many2many('ir.module.module', 'rel_modules_langexport', 'wiz_id', 'module_id', 'Modules To Export', domain=[('state','=','installed')]),
            'data': fields.binary('File', readonly=True),
            'advice': fields.text('Note', readonly=True),
            'state': fields.selection([('choose', 'choose'),   # choose language
                                       ('get', 'get')])        # get the file
    }
    _defaults = { 
        'state': 'choose',
        'name': 'lang.tar.gz',
        'lang': NEW_LANG_KEY,
        'format': 'csv',
    }

    def act_getfile(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids)[0]
        lang = this.lang if this.lang != NEW_LANG_KEY else False
        mods = map(lambda m: m.name, this.modules) or ['all']
        mods.sort()
        buf = cStringIO.StringIO()
        tools.trans_export(this.lang, mods, buf, this.format, cr)
        if this.format == 'csv':
            this.advice = _("Save this document as a .CSV file and open it with your favourite spreadsheet software. The file encoding is UTF-8. You have to translate the last column before reimporting it.")
        elif this.format == 'po':
            if not lang:
                this.format = 'pot'
            this.advice = _("Save this document as a %s file and edit it with a PO editor or a text editor. The file encoding is UTF-8.") % ('.'+this.format,)
        elif this.format == 'tgz':
            this.advice = _('Save this document as a .tgz file. This archive contains UTF-8 %s files and may be uploaded to launchpad.')
        filename = _('new')
        if lang:
            filename = get_iso_codes(this.lang)
        elif len(mods) == 1:
            filename = mods[0]
        this.name = "%s.%s" % (filename, this.format)
        out = base64.encodestring(buf.getvalue())
        buf.close()
        self.write(cr, uid, ids, {'state': 'get',
                                  'data': out,
                                  'advice': this.advice,
                                  'name':this.name}, context=context)
        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
