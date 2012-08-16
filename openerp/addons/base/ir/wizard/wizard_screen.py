# -*- coding: utf-8 -*-
##############################################################################
#    
#    Copyright (C) 2010 OpenERP s.a. (<http://www.openerp.com>).
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
import base64
import os
import random

import tools
from osv import fields,osv

# Simple base class for wizards that wish to use random images on the left
# side of the form.
class wizard_screen(osv.osv_memory):
    _name = 'ir.wizard.screen'

    def _get_image(self, cr, uid, context=None):
        path = os.path.join('base','res','config_pixmaps','%d.png'%random.randrange(1,4))
        image_file = file_data = tools.file_open(path,'rb')
        try:
            file_data = image_file.read()
            return base64.encodestring(file_data)
        finally:
            image_file.close()

    def _get_image_fn(self, cr, uid, ids, name, args, context=None):
        image = self._get_image(cr, uid, context)
        return dict.fromkeys(ids, image) # ok to use .fromkeys() as the image is same for all 

    _columns = {
        'config_logo': fields.function(_get_image_fn, string='Image', type='binary'),
    }

    _defaults = {
        'config_logo': _get_image
    }
wizard_screen()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
