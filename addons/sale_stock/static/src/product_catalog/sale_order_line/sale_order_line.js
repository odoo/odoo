/** @odoo-module */

import { ProductCatalogSOL } from "@sale/js/product_catalog/sale_order_line/sale_order_line";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductCatalogSOL, {
    props: {
        ...ProductCatalogSOL.props,
        deliveredQty: Number,
    },
});

patch(ProductCatalogSOL.prototype, {
    get disableRemove() {
        return this.props.quantity === this.props.deliveredQty;
    },
    get disabledButtonTooltip() {
        if (this.disableRemove) {
            return _t("The ordered quantity cannot be decreased below the amount already delivered. Instead, create a return in your inventory.");
        }
        return super.disabledButtonTooltip;
    },
});
