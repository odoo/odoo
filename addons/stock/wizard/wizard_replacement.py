##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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
