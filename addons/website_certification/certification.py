# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
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


class certification_type(osv.Model):
    _name = 'certification.type'
    _order = 'name ASC'
    _columns = {
        'name': fields.char("Certification Type", required=True)
    }


class certification_certification(osv.Model):
    _name = 'certification.certification'
    _order =  'certification_date DESC'
    _columns = {
        'partner_id': fields.many2one('res.partner', string="Partner", required=True),
        'type_id': fields.many2one('certification.type', string="Certification", required=True),
        'certification_date': fields.date("Certification Date", required=True),
        'certification_score': fields.char("Certification Score", required=True),
        'certification_hidden_score': fields.boolean("Hide score on website?")
    }
