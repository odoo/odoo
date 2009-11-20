# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import wizard

class wizard_replacement(wizard.interface):

    def getComposant(self, cr, uid, data, context):
        return {}

    def replaceComposant(self, cr, uid, data, context):
        return {}

    comp_form = '''<?xml version="1.0"?><form string="Replace a component"><label string="Component" colspan="4"/></form>'''
    comp_fields = {}

    replace_form = '''<?xml version="1.0"?><form string="Replace result"><label string="Replacing successful !" colspan="4" /></form>'''
    replace_fields = {}

    states = {
            'init' : {
                'actions' : [getComposant],
                'result' : {
                    'type' : 'form',
                    'arch' : comp_form,
                    'fields' : comp_fields,
                    'state' : [('end', 'Cancel'), ('replace', 'Replace')]}
                },
            'replace' : {
                'action' : [replaceComposant],
                'result' : {
                    'type' : 'form',
                    'arch' : replace_form,
                    'fields' : replace_fields,
                    'state' : [('end', 'Ok')]}
                },
            }

wizard_replacement('stock.move.replace')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

