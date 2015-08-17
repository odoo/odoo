# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError


class Product(models.Model):
    _inherit = 'product.template'
    membership = fields.Boolean('Membership', help='Check if the product is eligible for membership.')
    membership_date_from = fields.Date('Membership Start Date', help='Date from which membership becomes active.')
    membership_date_to = fields.Date('Membership End Date', help='Date until which membership remains active.')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        ModelData = self.env['ir.model.data']
        context = dict(self.env.context)
        if ('product' in context) and (context.get('product') == 'membership_product'):
            model_data_ids_form = ModelData.search([('model', '=', 'ir.ui.view'), ('name', 'in', ['membership_products_form', 'membership_products_tree'])])
            resource_id_form = ModelData.read(model_data_ids_form, fields=['res_id', 'name'])
            dict_model = {}
            for i in resource_id_form:
                dict_model[i.name] = i.res_id
            if view_type == 'form':
                view_id = dict_model['membership_products_form']
            else:
                view_id = dict_model['membership_products_tree']
        return super(Product, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
  
    _sql_constraints = [('membership_date_greater', 'check(membership_date_to >= membership_date_from)', 'Error ! Ending Date cannot be set before Beginning Date.')]
