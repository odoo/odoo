# -*- encoding: utf-8 -*-
from openerp.osv import fields, orm


class marcos_cjc_concept(orm.Model):
    _name = "marcos.cjc.concept"

    _columns = {
        'name': fields.char(u"Descripción", size=50, required=True),
        'supplier_taxes_id': fields.many2many('account.tax', 'cjc_supplier_taxes_rel', 'prod_id', 'tax_id', 'Impuestos', required=True,
                                              domain=[('parent_id', '=', False), ('type_tax_use', 'in', ['purchase', 'all'])]),
        'account_expense': fields.many2one('account.account', "Cuenta de gasto", required=True)

        # "product_id": fields.many2one("product.product", string="Producto", required=True),
        }
