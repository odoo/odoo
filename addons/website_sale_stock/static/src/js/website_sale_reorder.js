/** @odoo-module **/

import { ReorderDialog } from "@website_sale/js/website_sale_reorder";
import { patch } from "@web/core/utils/patch";
import { sprintf } from "@web/core/utils/strings";

patch(ReorderDialog.prototype, "website_sale_stock_reorder", {
    /**
     * @override
     */
    async onWillStartHandler() {
        const res = await this._super(...arguments);
        for (const product of this.content.products) {
            this.stockCheckCombinationInfo(product);
        }
        return res;
    },

    /**
     * @override
     */
    async loadProductCombinationInfo(product) {
        await this._super(...arguments);
    },

    stockCheckCombinationInfo(product) {
        // Products that should have a max quantity available should be limited by default.
        if (product.combinationInfo.allow_out_of_stock_order || product.type !== "product") {
            return;
        }
        product.max_quantity_available = product.combinationInfo.free_qty;
        if (!product.max_quantity_available) {
            product.add_to_cart_allowed = false;
        }
        if (product.max_quantity_available < product.qty) {
            product.qty_warning = sprintf(
                this.env._t("You ask for %s Units but only %s are available."),
                product.qty.toFixed(1),
                product.max_quantity_available.toFixed(1)
            );
            product.qty = product.max_quantity_available;
            product.stock_warning = true;
        } else if (product.combinationInfo.cart_qty) {
            product.qty_warning = sprintf(
                this.env._t("You already have %s Units in your cart."),
                product.combinationInfo.cart_qty.toFixed(1)
            );
        }
    },

    /**
     * @override
     */
    getWarningForProduct(product) {
        if (product.hasOwnProperty("max_quantity_available") && !product.max_quantity_available) {
            return this.env._t("This product is out of stock.");
        }
        return this._super(...arguments);
    },

    /**
     * @override
     */
    changeProductQty(product, newQty) {
        if (product.max_quantity_available && newQty > product.max_quantity_available) {
            product.qty_warning = sprintf(
                this.env._t("You ask for %s Units but only %s are available."),
                newQty.toFixed(1),
                product.max_quantity_available.toFixed(1)
            );
            product.stock_warning = true;
            newQty = product.max_quantity_available;
        } else if (product.stock_warning) {
            product.qty_warning = false;
            product.stock_warning = false;
        }
        this._super(product, newQty);
    },
});
