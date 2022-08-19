odoo.define('pos_sale_product_configurator.models', function (require) {
    "use strict";

    const { Gui } = require('point_of_sale.Gui');
    var { Order } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');


    const PosSaleProductConfiguratorOrder = (Order) => class PosSaleProductConfiguratorOrder extends Order {
        async add_product(product, options) {
            super.add_product(...arguments);
            if (product.optional_product_ids.length) {
                // The `optional_product_ids` only contains ids of the product templates and not the product itself
                // We don't load all the product template in the pos, so it'll be hard to know if the id comes from
                // a product available in POS. We send a quick cal to the back end to verify.
                const isProductLoaded = await this.pos.env.services.rpc(
                    {
                        model: 'product.product',
                        method: 'has_optional_product_in_pos',
                        args: [[product.id]]
                    }
                );
                if (isProductLoaded) {
                    const quantity = this.get_selected_orderline().get_quantity();
                    const info = await this.env.pos.getProductInfo(product, quantity);
                    Gui.showPopup('ProductInfoPopup', {info: info , product: product});
                }
            }
        }
    }
    Registries.Model.extend(Order, PosSaleProductConfiguratorOrder);
})
