# -*- encoding: utf-8 -*-
##############################################################################
#
#     Author: Tatár Attila <atta@nvm.ro>, Fekete Mihai <feketemihai@gmail.com>
#    Copyright (C) 2011-2014 TOTAL PC SYSTEMS (http://www.erpsystems.ro).
#    Copyright (C) 2014 Fekete Mihai
#    Copyright (C) 2014 Tatár Attila
#     Based on precedent versions developed by Fil System, Fekete Mihai
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
from openerp.osv import fields, osv
from openerp.tools.translate import _

class ro_config_settings(osv.TransientModel):
    """ Settings menu, romanian localization settings object """
    
    _name = 'ro.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
            'cnp_identify':fields.boolean(
                'Gather personal (CNP) data from physical persons',
                help=_("The individual who the sensitive personal data"
                       " is about must give explicit consent to the"
                       " processing.")),    
    }
    
    def get_default_cnp_identification(self, cr, uid, ids, context=None):
        cnp_status = self.pool.get("ir.config_parameter").get_param(
            cr, uid, "cnp_identify", context=context)        
        return {'cnp_identify': cnp_status}

    def set_cnp_identification(self, cr, uid, ids, context=None):
        config_parameters = self.pool.get("ir.config_parameter")
        for record in self.browse(cr, uid, ids, context=context):
            config_parameters.set_param(cr, uid, "cnp_identify",
                                        record.cnp_identify or '',
                                        context=context)
    
