# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP (<http://www.openerp.com>).
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

from openerp.osv import osv, fields

class res_partner(osv.Model):
    _inherit = 'res.partner'

    #
    # add related fields to test them
    #
    _columns = {
        # a regular one
        'related_company_partner_id': fields.related(
            'company_id', 'partner_id', type='many2one', obj='res.partner'),
        # a related field with a single field
        'single_related_company_id': fields.related(
            'company_id', type='many2one', obj='res.company'),
        # a related field with a single field that is also a related field!
        'related_related_company_id': fields.related(
            'single_related_company_id', type='many2one', obj='res.company'),
    }


from openerp import api, scope, models, fields

class res_partner(models.Model):
    _inherit = 'res.partner'

    name_size = fields.Integer(compute='compute_name_size', store=False)
    children_count = fields.Integer(compute='compute_children_count', store=True)

    @api.record
    @api.depends('name')
    def compute_name_size(self):
        self.name_size = len(self.name)

    # Note: we introduce this weird dependency in order to catch changes on both
    # fields 'child_ids' and 'parent_id'
    @api.record
    @api.depends('child_ids.parent_id')
    def compute_children_count(self):
        self.children_count = len(self.child_ids)

