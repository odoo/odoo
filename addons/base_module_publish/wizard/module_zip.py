# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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
import pooler
import addons
from tools.translate import _

def createzip(cr, uid, moduleid, context, b64enc=True, src=True):
    pool = pooler.get_pool(cr.dbname)
    module_obj = pool.get('ir.module.module')

    module = module_obj.browse(cr, uid, moduleid)

    if module.state != 'installed':
        raise wizard.except_wizard(_('Error'),
                _('Can not export module that is not installed!'))
    
    val = addons.get_module_as_zip(module.name, b64enc=b64enc, src=src)

    return {'module_file': val, 'module_filename': str(module.name) + '-' + \
            (module.installed_version or '0') + '.zip'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

