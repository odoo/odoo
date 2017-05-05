# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Sébastien BEAU
#    Copyright 2011-2013 Akretion
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

from openerp import models, fields, api
from openerp.addons.connector.session import ConnectorSession
from .event import on_product_price_changed


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # TODO implement set function and also support multi tax
    @api.one
    @api.depends('taxes_id', 'taxes_id.group_id')
    def _get_tax_group_id(self):
        taxes = self.taxes_id
        self.tax_group_id = taxes[0].group_id.id if taxes else False

    tax_group_id = fields.Many2one(
        comodel_name='account.tax.group',
        compute='_get_tax_group_id',
        string='Tax Group',
        help='Tax groups are used with some external '
             'system like Prestashop',
    )

    @api.multi
    def _price_changed(self, vals):
        """ Fire the ``on_product_price_changed`` on all the variants of
        the template if the price of the product could have changed.

        If one of the field used in a sale pricelist item has been
        modified, we consider that the price could have changed.

        There is no guarantee that's the price actually changed,
        because it depends on the pricelists.
        """
        type_model = self.env['product.price.type']
        price_fields = type_model.sale_price_fields()
        # restrict the fields to the template ones only, so if
        # the write has been done on product.product, we won't
        # update all the variants if a price field of the
        # variant has been changed
        tmpl_fields = [field for field in vals if field in self._fields]
        if any(field in price_fields for field in tmpl_fields):
            product_model = self.env['product.product']
            session = ConnectorSession(self.env.cr, self.env.uid,
                                       context=self.env.context)
            products = product_model.search(
                [('product_tmpl_id', 'in', self.ids)]
            )
            # when the write is done on the product.product, avoid
            # to fire the event 2 times
            if self.env.context.get('from_product_ids'):
                from_product_ids = self.env.context['from_product_ids']
                remove_products = product_model.browse(from_product_ids)
                products -= remove_products
            for product in products:
                on_product_price_changed.fire(session,
                                              product_model._name,
                                              product.id)

    @api.multi
    def write(self, vals):
        result = super(ProductTemplate, self).write(vals)
        self._price_changed(vals)
        return result


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends()
    def _get_checkpoint(self):
        checkpoint_model = self.env['connector.checkpoint']
        model_model = self.env['ir.model']
        model = model_model.search([('model', '=', 'product.product')])
        for product in self:
            points = checkpoint_model.search([('model_id', '=', model.id),
                                              ('record_id', '=', product.id),
                                              ('state', '=', 'need_review')],
                                             limit=1,
                                             )
            product.has_checkpoint = bool(points)

    has_checkpoint = fields.Boolean(compute='_get_checkpoint',
                                    string='Has Checkpoint')

    @api.multi
    def _price_changed(self, vals):
        """ Fire the ``on_product_price_changed`` if the price
        of the product could have changed.

        If one of the field used in a sale pricelist item has been
        modified, we consider that the price could have changed.

        There is no guarantee that's the price actually changed,
        because it depends on the pricelists.
        """
        type_model = self.env['product.price.type']
        price_fields = type_model.sale_price_fields()
        if any(field in price_fields for field in vals):
            session = ConnectorSession(self.env.cr, self.env.uid,
                                       context=self.env.context)
            for prod_id in self.ids:
                on_product_price_changed.fire(session, self._name, prod_id)

    @api.multi
    def write(self, vals):
        self_context = self.with_context(from_product_ids=self.ids)
        result = super(ProductProduct, self_context).write(vals)
        self._price_changed(vals)
        return result

    @api.model
    def create(self, vals):
        product = super(ProductProduct, self).create(vals)
        product._price_changed(vals)
        return product


class ProductPriceType(models.Model):
    _inherit = 'product.price.type'

    pricelist_item_ids = fields.One2many(
        comodel_name='product.pricelist.item',
        inverse_name='base',
        string='Pricelist Items',
        readonly=True,
    )

    @api.model
    def sale_price_fields(self):
        """ Returns a list of fields used by sale pricelists.
        Used to know if the sale price could have changed
        when one of these fields has changed.
        """
        item_model = self.env['product.pricelist.item']
        items = item_model.search(
            [('price_version_id.pricelist_id.type', '=', 'sale')],
        )
        types = self.search([('pricelist_item_ids', 'in', items.ids)])
        return [t.field for t in types]
