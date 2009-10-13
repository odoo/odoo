# -*- coding: utf-8 -*-
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

import os

import wizard
import netsvc
import time

_ups_form = '''<?xml version="1.0"?>
<form string="UPS XML generator">
    <separator string="UPS generator" colspan="4"/>
    <field name="weight" />
</form>'''

_ups_fields = {
    'weight' : { 'string' : 'Lot weight', 'type' : 'float', 'default' : lambda *a: 3.0, 'required' : True },
}

_ups_finalform = '''<?xml version="1.0"?>
<form string="UPS XML generator">
    <separator string="Save the attached file" colspan="4" />
    <field name="xmlfile" />
</form>'''

_ups_finalfields = {
    'xmlfile' : { 'string' : 'XML File', 'type' : 'binary' },
}

_ups_uploadform = '''<?xml version="1.0"?>
<form string="UPS XML generator">
    <separator string="File uploaded" colspan="4" />
</form>'''

_ups_uploadfields = {}

def create_xmlfile(self, cr, uid, data, context):
    report = netsvc._group['report']['report.stock.move.lot.ups_xml']
    data['report_type'] = 'raw'
    return {'xmlfile' : report.create(uid, data['ids'], data, {})}

def upload_xmlfile(self, cr, uid, data, context):
    report = netsvc._group['report']['report.stock.move.lot.ups_xml']
    data['report_type'] = 'raw'
#FIXME: this seems unfinished   
    fp = file('/tmp/test.xml', 'w').write(report.create(uid, data['ids'], data, {}))
    return {}

class wiz_ups(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch' : _ups_form, 'fields' : _ups_fields, 'state':[('end','Cancel'),('ups_save','Get xml file'), ('ups_upload', 'Upload xml file')]}
        },
        'ups_save': {
            'actions': [create_xmlfile],
            'result': {'type': 'form', 'arch' : _ups_finalform, 'fields' : _ups_finalfields, 'state':[('end', 'End')]}
        },
        'ups_upload' : {
            'actions' : [upload_xmlfile],
            'result' : {'type' : 'form', 'arch' : _ups_uploadform, 'fields' : _ups_uploadfields, 'state' : [('end', 'End')]}
        },
    }
wiz_ups('stock.ups_xml');


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

