# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import groupby
from odoo.exceptions import UserError

from odoo.addons.sale_shopee import utils


class ShopeeItem(models.Model):
    _name = 'shopee.item'
    _description = "Shopee Item"
    _check_company_auto = True

    shop_id = fields.Many2one(
        string="Shop", comodel_name='shopee.shop', ondelete='cascade', required=True
    )
    product_id = fields.Many2one(
        string="Product",
        comodel_name="product.product",
        ondelete='cascade',
        required=True,
        check_company=True,
    )
    shopee_model_identifier = fields.Char(string="Shopee Model ID")
    shopee_item_identifier = fields.Char(string="Shopee Item ID", required=True)
    company_id = fields.Many2one(related='shop_id.company_id')
    sync_to_shopee = fields.Boolean(string="Synchronize Inventory to Shopee", default=False)
    last_inventory_sync_date = fields.Datetime(
        string="Last Sync Date", readonly=True, default=fields.Datetime.now
    )

    _sql_constraints = [(
        'unique_shopee_item_and_model_identifiers',
        'UNIQUE(shop_id, shopee_item_identifier, shopee_model_identifier)',
        "Item and Model Identifiers must be unique for a given shop.",
    )]

    # === ACTION METHODS === #

    def action_sync_inventory(self):
        self._sync_inventory()

    # === BUSINESS METHODS === #

    def _sync_inventory(self, auto_commit=True):
        """ Synchronize the inventory from Odoo to Shopee.

        :param auto_commit: If True, the transaction will be committed after each successful sync
        :return: None
        """
        error_messages = []
        valid_items = self.filtered(
            lambda i: i.product_id.type == 'consu'
                      and i.product_id.is_storable
                      and i.sync_to_shopee
        ).sorted(lambda i: (i.last_inventory_sync_date, i.id))

        items_by_shop = dict(groupby(valid_items, lambda i: i.shop_id))

        for shop, all_items in items_by_shop.items():
            items_by_item_id = {}
            for item in all_items:
                items_by_item_id.setdefault(item.shopee_item_identifier, self.env['shopee.item'])
                items_by_item_id[item.shopee_item_identifier] += item

            # update item by item_id
            for shopee_item_identifier, items in items_by_item_id.items():
                try:
                    current_datetime = fields.Datetime.now()
                    utils.make_shopee_api_request(shop, 'update_stock', body={
                        'item_id': int(shopee_item_identifier),
                        'stock_list': [{
                            'model_id': int(item.shopee_model_identifier),
                            'seller_stock': [{'stock': int(item.product_id.free_qty)}]
                        } for item in items]
                    }, method='POST')
                    items.write({'last_inventory_sync_date': current_datetime})
                    if auto_commit:
                        self.env.cr.commit()
                except UserError as error:
                    error_messages.append({
                        'item_identifier': shopee_item_identifier,
                        'message': str(error),
                    })
        if error_messages:
            self.shop_id._handle_sync_failure(flow='inventory_sync', error_messages=error_messages)
