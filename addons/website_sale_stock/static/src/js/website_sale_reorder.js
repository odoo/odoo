/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ReorderDialog } from "@website_sale/js/website_sale_reorder";
import { patch } from "@web/core/utils/patch";

patch(ReorderDialog.prototype, {
    /**
     * @override
     */
    async onWillStartHandler() {
        const res = await super.onWillStartHandler(...arguments);
        for (const product of this.content.products) {
            this.stockCheckCombinationInfo(product);
        }
        return res;
    },

    /**
     * @override
     */
    async loadProductCombinationInfo(product) {
        await super.loadProductCombinationInfo(...arguments);
    },

    stockCheckCombinationInfo(product) {
        // Products that should have a max quantity available should be limited by default.
        if (product.combinationInfo.allow_out_of_stock_order || ! product.is_storable) {
            return;
        }
        product.max_quantity_available = product.combinationInfo.free_qty;
        if (!product.max_quantity_available) {
            product.add_to_cart_allowed = false;
        }
        if (product.max_quantity_available < product.qty) {
            product.qty_warning = _t(
                "You ask for %(quantity1)s Units but only %(quantity2)s are available.",
                {
                    quantity1: product.qty.toFixed(1),
                    quantity2: product.max_quantity_available.toFixed(1),
                }
            );
            product.qty = product.max_quantity_available;
            product.stock_warning = true;
        } else if (product.combinationInfo.cart_qty) {
            product.qty_warning = _t(
                "You already have %s Units in your cart.",
                product.combinationInfo.cart_qty.toFixed(1)
            );
        }
    },

    /**
     * @override
     */
    getWarningForProduct(product) {
        if (product.hasOwnProperty("max_quantity_available") && !product.max_quantity_available) {
            return _t("This product is out of stock.");
        }
        return super.getWarningForProduct(...arguments);
    },

    /**
     * @override
     */
    changeProductQty(product, newQty) {
        if (product.max_quantity_available && newQty > product.max_quantity_available) {
            product.qty_warning = _t(
                "You ask for %(quantity1)s Units but only %(quantity2)s are available.",
                {
                    quantity1: newQty.toFixed(1),
                    quantity2: product.max_quantity_available.toFixed(1),
                }
            );
            product.stock_warning = true;
            newQty = product.max_quantity_available;
        } else if (product.stock_warning) {
            product.qty_warning = false;
            product.stock_warning = false;
        }
        super.changeProductQty(product, newQty);
    },
});
