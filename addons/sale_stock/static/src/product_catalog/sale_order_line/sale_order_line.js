import { _t } from "@web/core/l10n/translation";
import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";

export class ProductCatalogSaleOrderLine extends ProductCatalogOrderLine {
    static props = {
        ...ProductCatalogOrderLine.props,
        deliveredQty: Number,
    }

    get disableRemove() {
        return this.props.quantity === this.props.deliveredQty;
    }

    get disabledButtonTooltip() {
        if (this.disableRemove) {
            return _t("The ordered quantity cannot be decreased below the amount already delivered. Instead, create a return in your inventory.");
        }
        return super.disabledButtonTooltip;
    }
}
