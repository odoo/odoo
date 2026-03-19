import { productProps, Product } from "@sale/js/product/product";
import { patch } from "@web/core/utils/patch";
import { t } from "@odoo/owl";

Object.assign(productProps, {
    strikethrough_price: t.number().optional(),
    base_unit_price: t.number().optional(),
    can_be_sold: t.boolean().optional(),
    free_qty: t.number().optional(),
    // The following fields are needed for tracking.
    category_name: t.string().optional(),
    currency_name: t.string().optional(),
});

patch(Product.prototype, {
    /**
     * Check whether this product is out of stock.
     *
     * @return {Boolean} - Whether this product is out of stock.
     */
    isOutOfStock() {
        return !this.env.isQuantityAllowed(this.props, 1);
    },
});
