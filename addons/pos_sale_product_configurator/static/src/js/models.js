odoo.define('pos_sale_product_configurator.models', function (require) {
    "use strict";

    const { Gui } = require('point_of_sale.Gui');
    var models = require('point_of_sale.models');

    models.load_fields("product.product", ["optional_product_ids"]);
    models.load_fields("pos.config", ["iface_open_product_info"]);

    const super_order_model = models.Order.prototype;
    models.Order = models.Order.extend({
        async add_product(product, options) {
            super_order_model.add_product.apply(this, arguments);
            if (this.pos.config.iface_open_product_info && product.optional_product_ids.length) {
                // The `optional_product_ids` only contains ids of the product templates and not the product itself
                // We don't load all the product template in the pos, so it'll be hard to know if the id comes from
                // a product available in POS. We send a quick cal to the back end to verify.
                const isProductLoaded = await this.pos.rpc(
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
    })
})
