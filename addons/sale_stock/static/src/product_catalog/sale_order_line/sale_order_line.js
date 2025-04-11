import { _t } from "@web/core/l10n/translation";
import { ProductCatalogSaleOrder } from "@sale/product_catalog/sale_order_line/sale_order_line";

export class ProductCatalogSaleOrderLine extends ProductCatalogSaleOrder {
    static props = {
        ...ProductCatalogSaleOrder.props,
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
