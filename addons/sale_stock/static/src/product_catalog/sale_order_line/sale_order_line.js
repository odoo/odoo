import { _t } from "@web/core/l10n/translation";
import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogOrderLine, {
    props: {
        ...ProductCatalogOrderLine.props,
        deliveredQty: { type: Number, optional: true },
    },
});

export class ProductCatalogSaleOrderLine extends ProductCatalogOrderLine {
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
