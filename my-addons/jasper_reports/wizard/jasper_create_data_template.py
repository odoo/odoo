# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Omar Castiñeira Saavedra <omar@pexego.es>
#                         Pexego Sistemas Informáticos http://www.pexego.es
# Copyright (C) 2013 Tadeus Prastowo <tadeus.prastowo@infi-nity.com>
#                         Vikasa Infinity Anugrah <http://www.infi-nity.com>
# Copyright (C) 2019-Today Serpent Consulting Services Pvt. Ltd.
#                         (<http://www.serpentcs.com>)
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

import base64
from odoo import fields, models


class CreateDataTemplate(models.TransientModel):

    _name = 'jasper.create.data.template'
    _description = 'Create Data Template'

    model_id = fields.Many2one('ir.model', required=True)
    depth = fields.Integer(required=True, default=1)
    filename = fields.Char('File Name', size=32)
    data = fields.Binary('XML')

    def action_create_xml(self):
        report_obj = self.env['ir.actions.report']
        for data_template in self:
            xml = report_obj.create_xml(
                data_template.model_id.model, data_template.depth)
            base64_str = base64.encodestring(
                ('%s' % (xml)).encode()).decode().replace('\n', '')
            data_template.write({
                'data': base64_str,
                'filename': str(data_template.model_id.name) + '_template.xml'})
            [action] = self.env.ref(
                'jasper_reports.action_jasper_create_date_template').read()
            action.update({'res_id': data_template.id})
            return action
