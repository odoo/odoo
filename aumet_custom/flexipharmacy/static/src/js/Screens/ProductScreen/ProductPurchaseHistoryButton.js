odoo.define('flexipharmacy.ProductPurchaseHistoryButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    var rpc = require('web.rpc');
    

    class ProductPurchaseHistoryButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('open-customer-purchase-history', this.OpenCustomerPurchaseHistory);
        }
        async OpenCustomerPurchaseHistory(){
            var self = this
            var product_data = {}
            if (self.env.pos.get_order().get_client()) {
                var product_id = this.env.pos.get_order().get_selected_orderline().product.id
                var partner_id = this.env.pos.get_order().get_client().id
                await rpc.query({
                    model: 'pos.order',
                    method: 'get_customer_product_history',
                    args: [Number(product_id), Number(partner_id)],
                }, {
                    async: false
                }).then(async function (res) {
                    if (res.length > 0) {
                        const { confirmed, payload: popup_data} = await self.showPopup('ProductHistoryPopup', {
                            product_data: res,
                        }); 
                    } else {
                        self.env.pos.db.notification('warning', "Product has no purchase history!");
                    }
                });
            } else {
                this.env.pos.db.notification('danger', "Please Select a Customer!");
            }
        }
    }

    ProductPurchaseHistoryButton.template = 'ProductPurchaseHistoryButton';

    Registries.Component.add(ProductPurchaseHistoryButton);

    return ProductPurchaseHistoryButton;
});
