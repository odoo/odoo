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

from openerp.osv import fields, osv

class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'manufacturer' : fields.many2one('res.partner', 'Manufacturer'),
        'manufacturer_pname' : fields.char('Manufacturer Product Name', size=64),
        'manufacturer_pref' : fields.char('Manufacturer Product Code', size=64),
        'attribute_ids': fields.one2many('product.manufacturer.attribute', 'product_id', 'Attributes'),
    }
product_product()

class product_attribute(osv.osv):
    _name = "product.manufacturer.attribute"
    _description = "Product attributes"
    _columns = {
        'name' : fields.char('Attribute', size=64, required=True),
        'value' : fields.char('Value', size=64),
        'product_id': fields.many2one('product.product', 'Product', ondelete='cascade'),
    }
product_attribute()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
